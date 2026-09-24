# Which landmarks carry the sibling-family signal? Family ICC of shape (after size and
# cross type) for anatomical subsets of each protocol, each subset superimposed on its own.
# Tests whether the old protocol's higher family resemblance on the Dorsal and Left faces
# comes from specific (e.g. ambiguous, hand-placed) points.
suppressMessages(library(geomorph)); set.seed(1)
src <- readLines("sibling_family_test.R")
eval(parse(text = src[grep("^read_cfg", src):(grep("^rows <- list", src) - 1)]))
schema <- jsonlite::fromJSON("../landmark_schema.json", simplifyVector = FALSE)
icc_sub <- function(view, which, sel_old = NULL, sel_new = NULL) {
  cfg <- read_cfg(view, which)
  if (which == "old") {
    A <- cfg$A[sel_old, , ]; g <- gpagen(A, print.progress = FALSE)
  } else {
    ids <- sapply(schema$views[[view]]$points, function(p) p$id)
    sel <- which(ids %in% sel_new | Reduce(`|`, lapply(c(sel_new[grepl("\\.", sel_new)], "zzz"), function(q) startsWith(ids, q))))
    sl <- as.matrix(read.csv(file.path("data", sprintf("%s_sliders_new.csv", view))))
    k <- sl[, 1] %in% sel & sl[, 2] %in% sel & sl[, 3] %in% sel
    s2 <- matrix(match(sl[k, ], sel), ncol = 3)
    g <- if (nrow(s2)) gpagen(cfg$A[sel, , ], curves = s2, ProcD = FALSE, print.progress = FALSE) else
      gpagen(cfg$A[sel, , ], print.progress = FALSE)
  }
  R <- resid_on(two.d.array(g$coords), log(g$Csize), factor(cfg$meta$group))
  round(icc(R, cfg$meta$family), 3)
}
out <- list(); add <- function(view, set, proto, v) out[[length(out) + 1]] <<- data.frame(view, subset = set, protocol = proto, family_icc = v)
# Dorsal face
add("Bottom", "all", "old", icc_sub("Bottom", "old", 1:17))
add("Bottom", "without split point 9", "old", icc_sub("Bottom", "old", setdiff(1:17, 9)))
add("Bottom", "without fork cluster 6-12", "old", icc_sub("Bottom", "old", setdiff(1:17, 6:12)))
add("Bottom", "fork cluster 6-12 only", "old", icc_sub("Bottom", "old", 6:12))
add("Bottom", "tips + sutures (shared region)", "new", icc_sub("Bottom", "new", sel_new = c("B01","B02","B03","B04","B05","B06","B07","B08","B09","B10","B14","B.medL","B.medS","B.outL","B.outS")))
add("Bottom", "sutures + apices only", "old", icc_sub("Bottom", "old", c(1, 2:5, 13, 14:17)))
add("Bottom", "sutures + apices only", "new", icc_sub("Bottom", "new", sel_new = c("B01","B02","B03","B04","B05","B06","B07","B08","B09","B10")))
add("Bottom", "shaft + shoulders + notch", "new", icc_sub("Bottom", "new", sel_new = c("B06","B10","B11","B12","B13","B.sideL","B.sideS")))
# Left face
add("Left", "all", "old", icc_sub("Left", "old", 1:32))
add("Left", "heel (old 1-3 / new heel)", "old", icc_sub("Left", "old", 1:3))
add("Left", "heel (old 1-3 / new heel)", "new", icc_sub("Left", "new", sel_new = c("L02","L03","L.heel")))
add("Left", "ventral margin + sutures", "old", icc_sub("Left", "old", 3:13))
add("Left", "ventral margin + sutures", "new", icc_sub("Left", "new", sel_new = c("L01","L02","L04","L05","L06","L07","L08","L09","L10","L.vbase","L.vdist")))
add("Left", "window", "old", icc_sub("Left", "old", 14:24))
add("Left", "window", "new", icc_sub("Left", "new", sel_new = c("L11","L12","L13","L14","L15","L16","L17","L.window")))
add("Left", "dorsal margin", "old", icc_sub("Left", "old", c(13, 26:32)))
add("Left", "dorsal margin", "new", icc_sub("Left", "new", sel_new = c("L01","L18","L.dorsal")))
add("Left", "without heel", "old", icc_sub("Left", "old", 4:32))
res <- do.call(rbind, out); write.csv(res, "output/sibling_family_modules.csv", row.names = FALSE); print(res, row.names = FALSE)
