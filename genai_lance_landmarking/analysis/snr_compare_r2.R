# Round 2 (Right, Left): signal-to-noise for three models on the corrected image set:
# old (v2 human points), new (v1.3, corrected dorsal start), newdistal (dorsal curve
# starting at the window's proximal end). Otherwise identical to snr_compare.R.
# Signal-to-noise of automated (CNN) measurement, old vs new protocol.
#
# Inputs (from cnn/run_protocol_comparison.sh -> export_predictions.py):
#   data/cnn/<View>_{manual,predicted}_test_{old,new}proto.csv  (ID, Group, px_per_mm, X1, Y1, ...)
#   data/<View>_sliders_new.csv                                   (new-protocol curves)
# For each face x protocol, label and prediction of every test specimen are
# superimposed together (new: sliding semilandmarks) and treated as two
# replicate measurements of the specimen (Klingenberg & McIntyre 1998; Fruciano 2016):
#   MS_among  = between-specimen mean square, MS_error = label-vs-prediction mean square
#   var_among = (MS_among - MS_error) / 2
#   repeatability = var_among / (var_among + MS_error);  signal/noise = var_among / MS_error
# computed for shape (Procrustes coordinates) and log centroid size, for all test
# specimens and for the backcrosses (LBX + PBX) only. A paired bootstrap over
# specimens gives 95% intervals and the new - old difference.
#
# usage: Rscript snr_compare.R  (from analysis/)
suppressMessages(library(geomorph))
set.seed(1); B <- 1000

read_pair <- function(view, proto) {
  f <- function(k) read.csv(file.path("data", "cnn_r2", sprintf("%s_%s_test_%sproto.csv", view, k, proto)))
  m <- f("manual"); p <- f("predicted")
  stopifnot(identical(m$ID, p$ID))
  xy <- rbind(as.matrix(m[, -(1:3)]), as.matrix(p[, -(1:3)]))
  A <- arrayspecs(xy, ncol(xy) / 2, 2); A[, 2, ] <- -A[, 2, ]
  list(A = A, id = c(m$ID, p$ID), group = c(m$Group, p$Group), n = nrow(m))
}

align <- function(d, view, proto) {
  if (proto != "old") {
    sl <- as.matrix(read.csv(file.path("data", sprintf("%s_sliders_new.csv", view))))
    gpagen(d$A, curves = sl, ProcD = FALSE, print.progress = FALSE)
  } else gpagen(d$A, print.progress = FALSE)
}

# mean squares for n specimens x 2 replicates; Y rows 1..n = labels, n+1..2n = predictions
ms <- function(Y, n) {
  Y <- as.matrix(Y)
  a <- Y[1:n, , drop = FALSE]; b <- Y[(n + 1):(2 * n), , drop = FALSE]
  m <- (a + b) / 2
  ss_err <- sum((a - m)^2) + sum((b - m)^2)
  ss_among <- 2 * sum(sweep(m, 2, colMeans(m))^2)
  c(among = ss_among / (n - 1), err = ss_err / n)
}
stats <- function(Y, n) {
  s <- ms(Y, n)
  va <- max((s["among"] - s["err"]) / 2, 0)
  c(rep = unname(va / (va + s["err"])), snr = unname(va / s["err"]))
}

rows <- list(); diffs <- list()
PROTOS <- c("old", "new", "newdistal")
for (view in c("Right", "Left")) {
  per <- list()
  for (proto in PROTOS) {
    d <- read_pair(view, proto)
    g <- align(d, view, proto)
    per[[proto]] <- list(shape = two.d.array(g$coords), lcs = matrix(log(g$Csize)), n = d$n,
                         group = d$group[1:d$n], id = d$id[1:d$n])
  }
  stopifnot(identical(per$old$id, per$new$id), identical(per$old$id, per$newdistal$id))
  n <- per$old$n
  subsets <- list(all = seq_len(n), backcrosses = which(per$old$group %in% c("LBX", "PBX")))
  for (sub in names(subsets)) {
    idx <- subsets[[sub]]
    for (what in c("shape", "lcs")) {
      pick <- function(p, i) p[[what]][c(i, i + n), , drop = FALSE]
      obs <- sapply(per, function(p) stats(pick(p, idx), length(idx)))
      bs <- replicate(B, {
        i <- sample(idx, length(idx), replace = TRUE)
        sapply(per, function(p) stats(pick(p, i), length(i)))
      })  # 2 stats x 2 protocols x B
      ci <- function(x) sprintf("%.3f [%.3f, %.3f]", median(x), quantile(x, .025), quantile(x, .975))
      for (proto in PROTOS) {
        rows[[length(rows) + 1]] <- data.frame(
          view, protocol = proto, subset = sub, measure = ifelse(what == "shape", "shape", "log centroid size"),
          n = length(idx), repeatability = ci(bs["rep", proto, ]), snr = ci(bs["snr", proto, ]),
          rep_observed = round(obs["rep", proto], 3), snr_observed = round(obs["snr", proto], 2))
      }
      for (cmp in list(c("new", "old"), c("newdistal", "old"), c("newdistal", "new"))) {
        diffs[[length(diffs) + 1]] <- data.frame(
          view, subset = sub, measure = ifelse(what == "shape", "shape", "log centroid size"), n = length(idx),
          comparison = paste(cmp[1], "-", cmp[2]),
          repeatability_difference = ci(bs["rep", cmp[1], ] - bs["rep", cmp[2], ]),
          share_first_higher = round(mean(bs["rep", cmp[1], ] > bs["rep", cmp[2], ]), 3))
      }
    }
  }
  cat(view, "done\n")
}
res <- do.call(rbind, rows); dif <- do.call(rbind, diffs)
# median pixel error from each run's eval_test.json, for reference
runs <- "/home/labradorite/g0-splits-project/lance_landmarking/model/runs/protocol_comparison_r2"
res$median_px_error <- mapply(function(v, p) {
  f <- file.path(runs, sprintf("%s_%s", p, v), "eval_test.json")
  if (file.exists(f)) round(jsonlite::fromJSON(f)$median_px_error, 1) else NA
}, res$view, res$protocol)
write.csv(res, "output/r2_snr_summary.csv", row.names = FALSE)
write.csv(dif, "output/r2_snr_differences.csv", row.names = FALSE)
print(res, row.names = FALSE); print(dif, row.names = FALSE)
