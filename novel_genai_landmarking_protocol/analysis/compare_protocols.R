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

results <- list()
hi_all <- list()
for (view in c("Right", "Left", "Bottom")) {
  for (which in c("old", "new")) {
    g <- gpa(view, which)
    m <- g$meta
    m$class <- factor(m$class, levels = c("lecontei", "F1", "LBX", "PBX", "pinetum"))
    m$session <- factor(m$session)
    gdf <- geomorph.data.frame(shape = g$fit$coords, logcs = log(g$fit$Csize),
                               class = m$class, session = m$session)
    # 1. group structure (type II SS: class after size and session)
    fit <- procD.lm(shape ~ logcs + session + class, data = gdf, iter = ITER, SS.type = "II",
                    print.progress = FALSE)
    at <- fit$aov.table
    r2 <- at["class", "Rsq"]; z <- at["class", "Z"]
    null <- procD.lm(shape ~ logcs + session, data = gdf, iter = ITER, print.progress = FALSE)
    pw <- summary(pairwise(fit, null, groups = gdf$class), test.type = "dist")$summary.table
    # 2. species among parents
    par <- m$class %in% c("lecontei", "pinetum")
    gp <- geomorph.data.frame(shape = g$fit$coords[, , par], logcs = log(g$fit$Csize[par]),
                              sp = droplevels(m$class[par]), session = droplevels(m$session[par]))
    sfit <- procD.lm(shape ~ logcs + session + sp, data = gp, iter = ITER, SS.type = "II",
                     print.progress = FALSE)
    s_r2 <- sfit$aov.table["sp", "Rsq"]; s_z <- sfit$aov.table["sp", "Z"]
    # 3. classification
    cl5 <- loo_lda(g$fit$coords, m$class)
    cl2 <- loo_lda(g$fit$coords[, , par], droplevels(m$class[par]))
    # 4. hybrid index
    h <- hybrid_index(g$fit$coords, m$class)
    hi <- tapply(h, m$class, median)
    hi_all[[paste(view, which)]] <- data.frame(view = view, protocol = which, key = m$key,
                                               class = m$class, h = h)
    # 5. disparity (Procrustes variance per class)
    disp <- morphol.disparity(shape ~ 1, groups = ~ class, data = gdf, iter = 99,
                              print.progress = FALSE)
    pv <- if (is.list(disp)) disp$Procrustes.var else disp
    results[[paste(view, which)]] <- data.frame(
      view = view, protocol = which, n = dim(g$fit$coords)[3], p = dim(g$fit$coords)[1],
      class_R2 = round(r2, 3), class_Z = round(z, 2),
      species_R2 = round(s_r2, 3), species_Z = round(s_z, 2),
      lda5_acc = round(cl5$acc, 3), lda5_k = cl5$k, lda_species_acc = round(cl2$acc, 3),
      hi_lecontei = round(hi["lecontei"], 2), hi_LBX = round(hi["LBX"], 2), hi_F1 = round(hi["F1"], 2),
      hi_PBX = round(hi["PBX"], 2), hi_pinetum = round(hi["pinetum"], 2),
      var_lec = signif(pv["lecontei"], 3), var_F1 = signif(pv["F1"], 3), var_LBX = signif(pv["LBX"], 3),
      var_PBX = signif(pv["PBX"], 3), var_pin = signif(pv["pinetum"], 3))
    write.csv(pw, file.path("output", sprintf("pairwise_%s_%s.csv", view, which)))
    capture.output(print(cl5$tab), file = file.path("output", sprintf("lda5_confusion_%s_%s.txt", view, which)))
    cat(view, which, "done\n")
  }
}
res <- do.call(rbind, results)
write.csv(res, file.path("output", "protocol_comparison_summary.csv"), row.names = FALSE)
write.csv(do.call(rbind, hi_all), file.path("output", "hybrid_index_individuals.csv"), row.names = FALSE)
print(res, row.names = FALSE)

# 6. per-module species effects: see module_species.R
