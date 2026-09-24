# Paired bootstrap: does one protocol separate the groups better than the other?
# Specimens are resampled (with replacement, stratified by class); the SAME resample
# is used for both protocols; each protocol's class R2 (5 groups) and species R2
# (lecontei vs pinetum parents) are computed after size and camera session
# (type II SS). Output: median and 95% interval of each statistic and of new - old.
suppressMessages({ library(geomorph); library(RRPP) })
set.seed(1); B <- 300
src <- readLines("compare_protocols.R"); eval(parse(text = src[26:45]))  # read_cfg, gpa
r2 <- function(Y, df, term) {
  f <- lm.rrpp(as.formula(paste("Y ~ logcs + session +", term)), data = df, iter = 0,
               SS.type = "II", print.progress = FALSE)
  a <- anova(f)$table
  a[term, "Rsq"]
}
out <- list()
for (view in c("Right", "Left", "Bottom")) {
  G <- lapply(c(old = "old", new = "new"), function(w) gpa(view, w))
  m <- G$old$meta
  stopifnot(identical(m$key, G$new$meta$key))
  cls <- factor(m$class); ses <- factor(m$session)
  Y <- lapply(G, function(g) two.d.array(g$fit$coords)); lc <- lapply(G, function(g) log(g$fit$Csize))
  byc <- split(seq_along(cls), cls)
  stat <- matrix(NA, B, 4, dimnames = list(NULL, c("cls_old", "cls_new", "sp_old", "sp_new")))
  for (b in 1:B) {
    idx <- unlist(lapply(byc, function(i) i[sample.int(length(i), length(i), replace = TRUE)]))
    par <- idx[cls[idx] %in% c("lecontei", "pinetum")]
    for (w in c("old", "new")) {
      d <- rrpp.data.frame(Y = Y[[w]][idx, ], logcs = lc[[w]][idx], session = droplevels(ses[idx]), class = droplevels(cls[idx]))
      stat[b, paste0("cls_", w)] <- r2(d$Y, d, "class")
      d2 <- rrpp.data.frame(Y = Y[[w]][par, ], logcs = lc[[w]][par], session = droplevels(ses[par]), sp = droplevels(cls[par]))
      stat[b, paste0("sp_", w)] <- r2(d2$Y, d2, "sp")
    }
  }
  q <- function(x) sprintf("%.3f [%.3f, %.3f]", median(x), quantile(x, .025), quantile(x, .975))
  for (e in c("cls", "sp")) {
    o <- stat[, paste0(e, "_old")]; n <- stat[, paste0(e, "_new")]
    out[[paste(view, e)]] <- data.frame(view, effect = ifelse(e == "cls", "class (5 groups)", "species (parents)"),
      R2_old = q(o), R2_new = q(n), new_minus_old = q(n - o), P_new_higher = round(mean(n > o), 3))
  }
  cat(view, "done\n")
}
res <- do.call(rbind, out)
write.csv(res, "output/bootstrap_old_vs_new.csv", row.names = FALSE)
print(res, row.names = FALSE)
