# Sibling-family test: does either protocol capture more between-family (heritable)
# variation in the backcrosses?
#
# Data: data/sib_<View>_{old,new}.csv (prep_sibling.py) - identical LBX/PBX individuals
# in families of >= 3. Old = v2 human points (fixed landmarks); new = v1.4 labels
# (sliding semilandmarks, data/<View>_sliders_new.csv).
# For each protocol: superimpose, remove log centroid size and cross type (LBX/PBX)
# from shape, then one-way ANOVA by family on the residual Procrustes coordinates:
#   ICC = var_among / (var_among + var_within),  var_among = (MS_family - MS_within) / n0
# i.e. the share of (size- and cross-corrected) shape variance lying between sibling
# families. The same for log centroid size. A cluster bootstrap over families
# (resampled within cross type, same resample for both protocols) gives 95%
# intervals and the new - old difference.
# Caveat: siblings may share imaging sessions/mounting, so family resemblance
# includes any batch effect; that affects both protocols equally.
#
# usage: Rscript sibling_family_test.R  (from analysis/)
suppressMessages(library(geomorph)); set.seed(1); B <- 1000

read_cfg <- function(view, which) {
  d <- read.csv(file.path("data", sprintf("sib_%s_%s.csv", view, which)), check.names = FALSE)
  xy <- as.matrix(d[, -(1:4)]); A <- arrayspecs(xy, ncol(xy) / 2, 2); A[, 2, ] <- -A[, 2, ]
  list(A = A, meta = d[, 1:4])
}
align <- function(cfg, view, which) {
  if (which == "new") {
    sl <- as.matrix(read.csv(file.path("data", sprintf("%s_sliders_new.csv", view))))
    gpagen(cfg$A, curves = sl, ProcD = FALSE, print.progress = FALSE)
  } else gpagen(cfg$A, print.progress = FALSE)
}
resid_on <- function(Y, lcs, grp) {  # remove size (if given) and cross type
  X <- if (is.null(lcs)) model.matrix(~ grp) else model.matrix(~ lcs + grp)
  Y - X %*% qr.solve(X, Y)
}
icc <- function(R, fam) {
  fam <- factor(fam); k <- nlevels(fam); N <- nrow(R); ni <- as.vector(table(fam))
  mu <- colMeans(R); means <- rowsum(R, fam) / ni
  ss_a <- sum(ni * rowSums(sweep(means, 2, mu)^2)); ss_w <- sum((R - means[as.integer(fam), , drop = FALSE])^2)
  ms_a <- ss_a / (k - 1); ms_w <- ss_w / (N - k); n0 <- (N - sum(ni^2) / N) / (k - 1)
  va <- max((ms_a - ms_w) / n0, 0); va / (va + ms_w)
}

rows <- list()
for (view in c("Right", "Left", "Bottom")) {
  P <- list()
  for (w in c("old", "new")) {
    cfg <- read_cfg(view, w); g <- align(cfg, view, w)
    lcs <- log(g$Csize); grp <- factor(cfg$meta$group)
    P[[w]] <- list(shape = resid_on(two.d.array(g$coords), lcs, grp),
                   size = resid_on(matrix(lcs), NULL, grp), meta = cfg$meta)
  }
  stopifnot(identical(P$old$meta$key, P$new$meta$key))
  meta <- P$old$meta
  fams <- split(seq_len(nrow(meta)), meta$family)
  fam_grp <- sapply(fams, function(i) meta$group[i[1]])
  for (what in c("shape", "size")) {
    obs <- sapply(P, function(p) icc(p[[what]], meta$family))
    bs <- replicate(B, {
      pick <- unlist(lapply(split(names(fams), fam_grp), function(f) sample(f, length(f), replace = TRUE)))
      idx <- unlist(lapply(seq_along(pick), function(j) fams[[pick[j]]]))
      fam_new <- rep(seq_along(pick), sapply(pick, function(f) length(fams[[f]])))
      sapply(P, function(p) icc(p[[what]][idx, , drop = FALSE], fam_new))
    })
    q <- function(x) sprintf("%.3f [%.3f, %.3f]", median(x), quantile(x, .025), quantile(x, .975))
    rows[[length(rows) + 1]] <- data.frame(
      view, measure = what, individuals = nrow(meta), families = length(fams),
      icc_old = round(obs["old"], 3), icc_new = round(obs["new"], 3),
      icc_old_boot = q(bs["old", ]), icc_new_boot = q(bs["new", ]),
      new_minus_old = q(bs["new", ] - bs["old", ]), share_new_higher = round(mean(bs["new", ] > bs["old", ]), 3))
  }
  cat(view, "done\n")
}
res <- do.call(rbind, rows)
write.csv(res, "output/sibling_family_test.csv", row.names = FALSE)
print(res, row.names = FALSE)
