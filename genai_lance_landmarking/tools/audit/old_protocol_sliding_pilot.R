suppressMessages({library(geomorph)})
base <- "/home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/Landmarked_Images"
load_view <- function(v, n){
  fs <- Sys.glob(file.path(base, "Landmarked_*", "txt", v, "*.txt"))
  L <- lapply(fs, function(f) as.matrix(read.table(f)))
  keep <- sapply(L, nrow) == n
  A <- simplify2array(L[keep]); A[,2,] <- -A[,2,]
  g <- factor(sub(".*Landmarked_([^/]+)/.*", "\\1", fs[keep]))
  list(A=A, g=g)
}
curv <- function(chain){ cbind(chain[-c(1,length(chain))]*0+chain[1:(length(chain)-2)], chain[2:(length(chain)-1)], chain[3:length(chain)]) }
run <- function(v, n, chains, drop=NULL){
  d <- load_view(v, n)
  fit0 <- gpagen(d$A, print.progress=FALSE)
  sl <- do.call(rbind, lapply(chains, curv))
  fit1 <- gpagen(d$A, curves=sl, ProcD=FALSE, print.progress=FALSE)
  r <- function(fit){ gdf <- geomorph.data.frame(shape=fit$coords, g=d$g)
    m <- procD.lm(shape~g, data=gdf, iter=199, print.progress=FALSE); m$aov.table$Rsq[1] }
  pc <- function(fit){ p <- gm.prcomp(fit$coords); round(100*p$sdev[1:3]^2/sum(p$sdev^2),1) }
  cat(sprintf("%s n=%d | all-fixed: group R2=%.3f PC1-3%%=%s | slid: group R2=%.3f PC1-3%%=%s | sliders=%d\n",
      v, dim(d$A)[3], r(fit0), paste(pc(fit0),collapse="/"), r(fit1), paste(pc(fit1),collapse="/"), nrow(sl)))
}
# Right: heel 1-2-3; ventral 10-11-12-13; dorsal 30-31-..-36-28-13; window 15-16-17-18-19-20-21-22-23
run("Right",36,list(c(1,2,3),c(10,11,12,13),c(30,31,32,33,34,35,36,28,13),c(15,16,17),c(17,18,19),c(19,20,21),c(21,22,23)))
run("Left",32,list(c(1,2,3),c(10,11,12,13),c(26,27,28,29,30,31,32,13),c(15,16,17),c(17,18,19),c(19,20,21),c(21,22,23)))
