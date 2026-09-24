# Same-region comparison: species effect per anatomical module, old vs new protocol,
# plus whole configurations with and without the new semilandmarks.
suppressMessages({ library(geomorph); library(RRPP) })
set.seed(1); ITER <- 999
src <- readLines("compare_protocols.R"); eval(parse(text = src[26:34]))  # read_cfg
schema <- jsonlite::fromJSON("../landmark_schema.json", simplifyVector = FALSE)
sp_effect <- function(A, meta, sl = NULL) {
  par <- meta$class %in% c("lecontei", "pinetum")
  fit <- if (!is.null(sl) && nrow(sl)) gpagen(A[, , par], curves = sl, ProcD = FALSE, print.progress = FALSE) else
    gpagen(A[, , par], print.progress = FALSE)
  gd <- geomorph.data.frame(shape = fit$coords, sp = droplevels(factor(meta$class[par])),
                            session = factor(meta$session[par]), logcs = log(fit$Csize))
  f <- procD.lm(shape ~ logcs + session + sp, data = gd, iter = ITER, SS.type = "II", print.progress = FALSE)
  c(R2 = round(f$aov.table["sp", "Rsq"], 3), Z = round(f$aov.table["sp", "Z"], 2))
}
new_sub <- function(view, pref) {
  cfg <- read_cfg(view, "new"); ids <- sapply(schema$views[[view]]$points, function(p) p$id)
  sl <- as.matrix(read.csv(file.path("data", sprintf("%s_sliders_new.csv", view))))
  sel <- which(ids %in% pref | Reduce(`|`, lapply(c(pref[grepl("\\.", pref)], "zzz"), function(q) startsWith(ids, q))))
  keep <- sl[, 1] %in% sel & sl[, 2] %in% sel & sl[, 3] %in% sel
  list(A = cfg$A[sel, , ], meta = cfg$meta, sl = matrix(match(sl[keep, ], sel), ncol = 3))
}
old_sub <- function(view, idx) { cfg <- read_cfg(view, "old"); list(A = cfg$A[idx, , ], meta = cfg$meta) }
out <- list()
add <- function(view, module, proto, x) out[[length(out) + 1]] <<- data.frame(view, module, protocol = proto, n_points = dim(x$A)[1], t(sp_effect(x$A, x$meta, x$sl)))
# Right: old heel 1-3 / ventral 4-13 / window 14-25 / dorsal 28-36
add("Right", "heel", "old", old_sub("Right", 1:3));            add("Right", "heel", "new", new_sub("Right", c("R02","R03","R.heel")))
add("Right", "ventral", "old", old_sub("Right", 3:13));        add("Right", "ventral", "new", new_sub("Right", c("R01","R02","R04","R05","R06","R07","R08","R09","R10","R.vbase","R.vdist")))
add("Right", "window", "old", old_sub("Right", 14:25));        add("Right", "window", "new", new_sub("Right", c("R11","R12","R13","R14","R15","R16","R17","R.window")))
add("Right", "dorsal", "old", old_sub("Right", c(13, 28, 30:36))); add("Right", "dorsal", "new", new_sub("Right", c("R01","R18","R.dorsal")))
add("Left", "heel", "old", old_sub("Left", 1:3));              add("Left", "heel", "new", new_sub("Left", c("L02","L03","L.heel")))
add("Left", "ventral", "old", old_sub("Left", 3:13));          add("Left", "ventral", "new", new_sub("Left", c("L01","L02","L04","L05","L06","L07","L08","L09","L10","L.vbase","L.vdist")))
add("Left", "window", "old", old_sub("Left", 14:24));          add("Left", "window", "new", new_sub("Left", c("L11","L12","L13","L14","L15","L16","L17","L.window")))
add("Left", "dorsal", "old", old_sub("Left", c(13, 26:32)));   add("Left", "dorsal", "new", new_sub("Left", c("L01","L18","L.dorsal")))
# Bottom: old tips region only (it never measured the shaft/base)
add("Bottom", "tips+sutures", "old", old_sub("Bottom", 1:17))
add("Bottom", "tips+sutures", "new", new_sub("Bottom", c("B01","B02","B03","B04","B05","B06","B07","B08","B09","B10","B14","B.medL","B.medS","B.outL","B.outS")))
add("Bottom", "shaft+shoulders+notch", "new", new_sub("Bottom", c("B06","B10","B11","B12","B13","B.sideL","B.sideS")))
# whole configurations: new anchors only (no semilandmarks) vs full new vs old
for (v in c("Right", "Left", "Bottom")) {
  ids <- sapply(schema$views[[v]]$points, function(p) p$id)
  roles <- sapply(schema$views[[v]]$points, function(p) p$role)
  add(v, "WHOLE anchors+computed only", "new", new_sub(v, ids[roles != "semilandmark"]))
  add(v, "WHOLE full", "new", new_sub(v, ids))
  cfg <- read_cfg(v, "old"); add(v, "WHOLE full", "old", list(A = cfg$A, meta = cfg$meta))
}
res <- do.call(rbind, out)
write.csv(res, "output/module_old_vs_new_species.csv", row.names = FALSE)
print(res, row.names = FALSE)
