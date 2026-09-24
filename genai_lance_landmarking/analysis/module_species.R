# Biological signal: old (v2) vs new (v1.3) landmarking protocol on the same specimens.
#
# Inputs: analysis/data/<View>_{old,new}.csv and <View>_sliders_new.csv
#         (from prep_protocol_comparison.py).
# For each view, both protocols get the same analyses:
#   1. Group structure  shape ~ log(CS) + session + class   (Procrustes ANOVA, RRPP)
#      -> R2 and effect size Z for class; pairwise class distances with p-values
#   2. Species          lecontei vs pinetum among parents, controlling for session
#   3. Classification   leave-one-out LDA on shape PCs: how often each specimen's
#                       class (lecontei / pinetum / F1 / LBX / PBX) is recovered
#   4. Hybrid index     each class mean projected onto the lecontei->pinetum axis
#                       (0 = lecontei mean, 1 = pinetum mean): expect LBX < F1 < PBX,
#                       and backcross individuals spread along the axis
#   5. Disparity        within-class shape variance (segregating backcrosses should
#                       exceed F1 and parents)
#   6. New-protocol modules: where the species signal sits (separate GPA per module)
# Old configurations are analysed as fixed landmarks (as in the original analyses);
# new ones with sliding semilandmarks (bending energy).
#
# usage: Rscript compare_protocols.R  (from analysis/)
suppressMessages({ library(geomorph); library(RRPP); library(MASS) })
set.seed(1)
ITER <- 999
dir.create("output", showWarnings = FALSE)

read_cfg <- function(view, which) {
  d <- read.csv(file.path("data", sprintf("%s_%s.csv", view, which)), check.names = FALSE)
  xy <- as.matrix(d[, -(1:5)])
  p <- ncol(xy) / 2
  A <- arrayspecs(xy, p, 2)
  A[, 2, ] <- -A[, 2, ]  # image y down -> up
  dimnames(A)[[3]] <- d$key
  list(A = A, meta = d[, 1:5])
}

gpa <- function(view, which) {
  cfg <- read_cfg(view, which)
  if (which == "new") {
    sl <- as.matrix(read.csv(file.path("data", sprintf("%s_sliders_new.csv", view))))
    fit <- gpagen(cfg$A, curves = sl, ProcD = FALSE, print.progress = FALSE)
  } else {
    fit <- gpagen(cfg$A, print.progress = FALSE)
  }
  list(fit = fit, meta = cfg$meta)
}

loo_lda <- function(coords, cls, maxpc = 20) {
  X <- two.d.array(coords)
  pc <- prcomp(X)
  k <- min(maxpc, floor(min(table(cls)) - 1), ncol(pc$x))
  S <- pc$x[, 1:k, drop = FALSE]
  pred <- lda(S, grouping = cls, CV = TRUE)$class
  list(acc = mean(pred == cls), tab = table(true = cls, pred = pred), k = k)
}

hybrid_index <- function(coords, cls) {
  X <- two.d.array(coords)
  ml <- colMeans(X[cls == "lecontei", , drop = FALSE])
  mp <- colMeans(X[cls == "pinetum", , drop = FALSE])
  ax <- mp - ml
  h <- as.vector((X - matrix(ml, nrow(X), ncol(X), byrow = TRUE)) %*% ax) / sum(ax^2)
  h
}

# 6. new-protocol modules: species effect per module (separate GPA per module)
schema <- jsonlite::fromJSON("../landmark_schema.json", simplifyVector = FALSE)
modules <- list(
  Right = list(heel = c("R02", "R03", "R.heel"), ventral = c("R04","R05","R06","R07","R08","R09","R10","R.vbase","R.vdist","R01"),
               dorsal = c("R18", "R.dorsal", "R01"), window = c("R11","R12","R13","R14","R15","R16","R17","R.window")),
  Left = list(heel = c("L02", "L03", "L.heel"), ventral = c("L04","L05","L06","L07","L08","L09","L10","L.vbase","L.vdist","L01"),
              dorsal = c("L18", "L.dorsal", "L01"), window = c("L11","L12","L13","L14","L15","L16","L17","L.window")),
  Bottom = list(tips = c("B01","B02","B14","B.medL","B.medS","B.outL","B.outS","B03","B07"),
                sutures = c("B03","B04","B05","B06","B07","B08","B09","B10"),
                shaft_shoulders = c("B06","B10","B11","B12","B13","B.sideL","B.sideS")))
mod_res <- list()
for (view in names(modules)) {
  cfg <- read_cfg(view, "new")
  ids <- sapply(schema$views[[view]]$points, function(p) p$id)
  sl <- as.matrix(read.csv(file.path("data", sprintf("%s_sliders_new.csv", view))))
  par <- cfg$meta$class %in% c("lecontei", "pinetum")
  for (mn in names(modules[[view]])) {
    pref <- modules[[view]][[mn]]
    sel <- which(ids %in% pref | Reduce(`|`, lapply(pref[grepl("\\.", pref)], function(q) startsWith(ids, q))))
    A <- cfg$A[sel, , par]
    # keep only sliders fully inside the module, re-indexed
    keep <- sl[, 1] %in% sel & sl[, 2] %in% sel & sl[, 3] %in% sel
    s2 <- matrix(match(sl[keep, ], sel), ncol = 3)
    fitm <- tryCatch(if (nrow(s2)) gpagen(A, curves = s2, ProcD = FALSE, print.progress = FALSE) else
      gpagen(A, print.progress = FALSE), error = function(e) { cat(view, mn, "GPA error:", conditionMessage(e), "\n"); NULL })
    if (is.null(fitm)) next
    gd <- geomorph.data.frame(shape = fitm$coords, sp = droplevels(factor(cfg$meta$class[par])),
                              session = factor(cfg$meta$session[par]))
    f <- procD.lm(shape ~ session + sp, data = gd, iter = ITER, SS.type = "II", print.progress = FALSE)
    mod_res[[paste(view, mn)]] <- data.frame(view = view, module = mn, n_points = length(sel),
                                             species_R2 = round(f$aov.table["sp", "Rsq"], 3),
                                             species_Z = round(f$aov.table["sp", "Z"], 2))
  }
}
mr <- do.call(rbind, mod_res)
write.csv(mr, file.path("output", "new_protocol_modules_species.csv"), row.names = FALSE)
print(mr, row.names = FALSE)
