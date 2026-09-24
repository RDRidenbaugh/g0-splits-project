# Right face, new protocol: how much of the lower repeatability comes from the
# start of the dorsal curve (R18 + first dorsal semilandmarks) and from one outlier image?
suppressMessages(library(geomorph)); set.seed(1); B <- 1000
src <- readLines("snr_compare.R"); i <- grep("^read_pair", src); j <- grep("^rows <- list", src)
eval(parse(text = src[i:(j - 1)]))
schema <- jsonlite::fromJSON("../landmark_schema.json", simplifyVector = FALSE)
ids <- sapply(schema$views$Right$points, function(p) p$id)
sl <- as.matrix(read.csv("data/Right_sliders_new.csv"))
run <- function(drop_ids = character(0), drop_key = NULL, label) {
  out <- list()
  for (proto in c("old", "new")) {
    d <- read_pair("Right", proto)
    keep_spec <- if (is.null(drop_key)) rep(TRUE, d$n) else d$id[1:d$n] != drop_key
    n <- sum(keep_spec); A <- d$A[, , c(keep_spec, keep_spec)]
    if (proto == "new") {
      keep <- which(!ids %in% drop_ids)
      k <- sl[, 1] %in% keep & sl[, 2] %in% keep & sl[, 3] %in% keep
      s2 <- matrix(match(sl[k, ], keep), ncol = 3)
      g <- gpagen(A[keep, , ], curves = s2, ProcD = FALSE, print.progress = FALSE)
    } else g <- gpagen(A, print.progress = FALSE)
    out[[proto]] <- two.d.array(g$coords)
  }
  obs <- sapply(out, function(Y) stats(Y, n)["rep"])
  bs <- replicate(B, { i <- sample(n, n, TRUE); sapply(out, function(Y) stats(Y[c(i, i + n), ], n)["rep"]) })
  dd <- bs[2, ] - bs[1, ]
  cat(sprintf("%-55s n=%d  old %.3f  new %.3f  new-old %.3f [%.3f, %.3f]\n", label, n, obs[1], obs[2],
              median(dd), quantile(dd, .025), quantile(dd, .975)))
  res[[length(res) + 1]] <<- data.frame(analysis = label, n = n, rep_old = round(obs[1], 3), rep_new = round(obs[2], 3),
    new_minus_old = sprintf("%.3f [%.3f, %.3f]", median(dd), quantile(dd, .025), quantile(dd, .975)))
}
res <- list()
prox <- c("R18", paste0("R.dorsal", 1:5))
run(label = "as analysed")
run(drop_key = "ll297xll283-1_r42", label = "without outlier image ll297xll283-1_r42")
run(drop_ids = prox, label = "new without R18 + dorsal 1-5")
run(drop_ids = c("R18", paste0("R.dorsal", 1:10)), label = "new without the whole dorsal curve")
run(drop_ids = prox, drop_key = "ll297xll283-1_r42", label = "without outlier AND without R18 + dorsal 1-5")
write.csv(do.call(rbind, res), "output/snr_ablation_right.csv", row.names = FALSE)
