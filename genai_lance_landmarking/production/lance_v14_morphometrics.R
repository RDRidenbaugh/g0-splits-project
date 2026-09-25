# Lance protocol v1.4: shape (GPA + PCA), centroid size and linear measures per view.
# Input:  Lance<View>_v14_XY.csv + Lance<View>_v14_sliders.csv from export_geomorph.py (mm).
#         Point numbers below follow landmark_key_v14.csv (e.g. Right: 1 = R01 apex, 18 = R18 dorsal curve start).
# Output: PRIME_Lance<View>_Pheno_v14.csv -- ID, species, session, centroid size, Comp1..,
#         linear measures (mm, degrees) -- one row per individual, joins to the QTL tables by ID
#         (see lance_landmarking/qtl/qtl/lance_qtl_analysis_v2.R).
library(dplyr)
library(geomorph)

in_dir <- Sys.getenv("LANCE_XY_DIR", "//wsl.localhost/Ubuntu/home/labradorite/g0-splits-project/genai_lance_landmarking/production/output/geomorph")
setwd(in_dir)
n_pcs <- 20            # shape PCs kept in the phenotype table
use_flagged <- FALSE   # TRUE keeps images that failed QC (qc_pass == FALSE)
species_levels <- c("Lecontei", "LBX", "F1", "PBX", "Pinetum")

## Helpers: all take the data frame and point numbers ##
pt <- function(df, a) cbind(df[[paste0("X", a)]], df[[paste0("Y", a)]])
# straight-line distance, as in combined_landmark_analysis_v1.R
dist_lm <- function(df, a, b) sqrt(((df[[paste0("X", a)]] - df[[paste0("X", b)]])^2) + ((df[[paste0("Y", a)]] - df[[paste0("Y", b)]])^2))
# length along a chain of points (curve arc length)
arc_len <- function(df, chain) Reduce(`+`, Map(function(a, b) dist_lm(df, a, b), head(chain, -1), tail(chain, -1)))
# angle at vertex v between points a and b, degrees
angle_at <- function(df, a, v, b) {
  u <- pt(df, a) - pt(df, v); w <- pt(df, b) - pt(df, v)
  acos(pmin(1, pmax(-1, rowSums(u * w) / sqrt(rowSums(u^2) * rowSums(w^2))))) * 180 / pi
}
# angle between the line a -> b and the axis u, degrees (0 = parallel)
angle_to_axis <- function(df, a, b, u) {
  w <- pt(df, b) - pt(df, a)
  acos(pmin(1, abs(rowSums(w * u)) / sqrt(rowSums(w^2)))) * 180 / pi
}
# unit axis from point p0 towards p1 (p1 may be a matrix, e.g. a midpoint)
unit_axis <- function(p0, p1) { u <- p1 - p0; u / sqrt(rowSums(u^2)) }
# position of point a along the axis starting at p0
along <- function(df, a, p0, u) rowSums((pt(df, a) - p0) * u)
# perpendicular distance of point a from the axis through p0
across <- function(df, a, p0, u) abs((pt(df, a) - p0)[, 1] * u[, 2] - (pt(df, a) - p0)[, 2] * u[, 1])
# perpendicular distance of point m from the chord a-b (scallop amplitude)
off_chord <- function(df, m, a, b) across(df, m, pt(df, a), unit_axis(pt(df, a), pt(df, b)))
# distance from point a, along the normal to axis u, to where that line crosses the polyline `chain`
# (height of the lance above a ventral point); NA if the normal misses the curve
height_to <- function(df, a, u, chain) {
  n <- cbind(-u[, 2], u[, 1]); p <- pt(df, a); out <- rep(NA_real_, nrow(df))
  for (k in seq_len(length(chain) - 1)) {
    q0 <- pt(df, chain[k]); q1 <- pt(df, chain[k + 1]); e <- q1 - q0
    den <- n[, 1] * e[, 2] - n[, 2] * e[, 1]
    s <- ((q0 - p)[, 1] * e[, 2] - (q0 - p)[, 2] * e[, 1]) / den     # distance along the normal
    t <- ((q0 - p)[, 1] * n[, 2] - (q0 - p)[, 2] * n[, 1]) / den     # position on the segment
    hit <- is.finite(s) & t >= 0 & t <= 1
    out <- ifelse(hit & (is.na(out) | abs(s) < out), abs(s), out)
  }
  out
}

## Linear measures, lateral faces ##
lateral_measures <- function(df, side) {
  # side "right": R.vdist = 25:28, R.dorsal = 29:38, R.window = 39:42; "left": L.vdist = 25:26, L.dorsal = 27:36, L.window = 37:40
  vdist <- if (side == "right") 25:28 else 25:26
  dorsal <- if (side == "right") 29:38 else 27:36
  window <- if (side == "right") 39:42 else 37:40
  dorsal_chain <- c(18, dorsal, 1)                              # dorsal curve start -> apex
  u <- unit_axis(pt(df, 2), pt(df, 1))                          # lance axis: heel-ventral junction -> apex
  m <- data.frame(ID = df$ID)
  m$Cutwindow_length <- dist_lm(df, 11, 17)                     # window proximal -> distal end
  for (k in 1:6) m[[paste0("Sut", k, "_length")]] <- dist_lm(df, 10 + k, 3 + k)          # dorsal end (window) -> ventral end
  for (k in 1:6) m[[paste0("Sut", k, "_angle")]] <- angle_to_axis(df, 3 + k, 10 + k, u)  # suture inclination to the lance axis
  n_arc <- if (side == "right") 6 else 5
  for (k in 1:n_arc) m[[paste0("Arc", k, "_width")]] <- dist_lm(df, 3 + k, 4 + k)       # ventral suture spacing
  if (side == "left") m$Sut6_to_split <- dist_lm(df, 9, 10)                             # L09 -> ventral split point L10
  for (k in 1:6) m[[paste0("Dorsal_arc", k, "_width")]] <- dist_lm(df, 10 + k, 11 + k)  # dorsal suture-end spacing, R11..R17
  for (k in 1:4) m[[paste0("Scallop", k, "_amp")]] <- off_chord(df, window[k], 11 + k, 12 + k)  # window crest height above its suture-end chord
  m$Face_length <- dist_lm(df, 3, 1)                            # heel notch -> apex
  m$Blade_chord <- dist_lm(df, 2, 1)                            # heel-ventral junction -> apex
  m$Heel_length <- dist_lm(df, 3, 2)                            # heel notch -> heel-ventral junction
  m$Heel_arc_length <- arc_len(df, c(3, 19:22, 2))
  m$Ventral_arc_length <- arc_len(df, c(2, 23:24, 4:10, vdist, 1))   # blade length along the ventral margin
  m$Dorsal_arc_length <- arc_len(df, dorsal_chain)                   # blade length along the dorsal margin (from R18)
  m$Tip_length <- dist_lm(df, 10, 1)                            # last ventral point -> apex
  m$Window_to_apex <- dist_lm(df, 17, 1)
  m$Height_window_start <- dist_lm(df, 11, 18)                  # window proximal end -> dorsal edge (perpendicular by construction)
  # ventral suture ends -> dorsal edge, perpendicular to the axis; sutures 1-2 lie proximal to the
  # dorsal curve's start (R18/L18), so heights start at suture 3. Left point 10 is the ventral split.
  for (k in 3:(if (side == "right") 7 else 6)) m[[paste0("Height_sut", k)]] <- height_to(df, 3 + k, u, dorsal_chain)
  if (side == "left") m$Height_split <- height_to(df, 10, u, dorsal_chain)
  for (k in 2:6) m[[paste0("Band_height_sut", k)]] <- height_to(df, 10 + k, u, dorsal_chain)  # dorsal suture end -> dorsal edge ("cutting depth")
  names(m)[-1] <- paste0(names(m)[-1], "_", side)
  m
}

## Linear measures, bottom ##
bottom_measures <- function(df) {
  p0 <- pt(df, 11)                                              # median basal notch B11
  apex_mid <- (pt(df, 1) + pt(df, 2)) / 2
  u <- unit_axis(p0, apex_mid)                                  # lance axis: B11 -> midpoint of the apices
  m <- data.frame(ID = df$ID)
  m$Long_half_length <- dist_lm(df, 14, 1)                      # fork crotch -> long apex
  m$Short_half_length <- dist_lm(df, 14, 2)
  m$Apex_separation <- dist_lm(df, 1, 2)
  m$Fork_depth <- sqrt(rowSums((pt(df, 14) - apex_mid)^2))      # fork crotch -> apex midpoint
  m$Inner_angle <- angle_at(df, 1, 14, 2)                       # apices seen from the crotch
  m$Tip_divergence_angle <- angle_at(df, 15, 14, 18)            # first medial semilandmarks of each tip at B14
  m$Dorsal_length_long <- along(df, 1, p0, u)                   # whole-structure length along the axis
  m$Dorsal_length_short <- along(df, 2, p0, u)
  m$Apex_offset <- m$Dorsal_length_long - m$Dorsal_length_short # long-short half length asymmetry
  m$Shoulder_span <- dist_lm(df, 12, 13)
  m$Shoulder_pos_long <- along(df, 12, p0, u)                   # B11 -> shoulder, along the axis
  m$Shoulder_pos_short <- along(df, 13, p0, u)
  m$Shoulder_to_apex_long <- m$Dorsal_length_long - m$Shoulder_pos_long
  m$Shoulder_to_apex_short <- m$Dorsal_length_short - m$Shoulder_pos_short
  m$Shoulder_lat_long <- across(df, 12, p0, u)                  # shoulder distance from the axis
  m$Shoulder_lat_short <- across(df, 13, p0, u)
  m$Shoulder_asym_pos <- m$Shoulder_pos_long - m$Shoulder_pos_short
  m$Shoulder_asym_lat <- m$Shoulder_lat_long - m$Shoulder_lat_short
  for (k in 1:4) m[[paste0("Width_sut", k)]] <- dist_lm(df, 2 + k, 6 + k)   # width across the k-th suture pair from the apex
  sut1_mid <- along(df, 3, p0, u) / 2 + along(df, 7, p0, u) / 2
  shoulder_mid <- (m$Shoulder_pos_long + m$Shoulder_pos_short) / 2
  m$Shaft_taper <- (m$Shoulder_span - m$Width_sut1) / (sut1_mid - shoulder_mid)  # width gained per mm towards the base
  m$Tip_outer_arc_long <- arc_len(df, c(3, 21:23, 1))
  m$Tip_outer_arc_short <- arc_len(df, c(7, 24:26, 2))
  m$Tip_medial_arc_long <- arc_len(df, c(14, 15:17, 1))
  m$Tip_medial_arc_short <- arc_len(df, c(14, 18:20, 2))
  m$Side_arc_long <- arc_len(df, c(6, 27:32, 12))               # outer margin, 4th suture -> shoulder
  m$Side_arc_short <- arc_len(df, c(10, 33:38, 13))
  names(m)[-1] <- paste0(names(m)[-1], "_bot")
  m
}

## Per view: GPA with sliding semilandmarks, PCA, centroid size, linear measures ##
run_view <- function(view) {
  lance <- read.csv(sprintf("Lance%s_v14_XY.csv", view), na.strings = "NA")
  if (!use_flagged) lance <- filter(lance, qc_pass)
  lance <- filter(lance, !is.na(X1))
  lance$species <- factor(lance$species, levels = species_levels)
  xy_cols <- grep("^[XY][0-9]+$", names(lance))
  n_lm <- length(xy_cols) / 2
  sliders <- as.matrix(read.csv(sprintf("Lance%s_v14_sliders.csv", view)))

  lance_array <- arrayspecs(lance[, xy_cols], n_lm, 2)
  dimnames(lance_array)[[3]] <- lance$ID
  lance_gpa <- gpagen(lance_array, curves = sliders, ProcD = FALSE, print.progress = FALSE)
  lance_pca <- gm.prcomp(lance_gpa$coords)

  v <- tolower(view)
  scores <- data.frame(ID = lance$ID, lance_gpa$Csize, lance_pca$x[, 1:min(n_pcs, ncol(lance_pca$x))])
  names(scores)[2] <- paste0("centroid_size_", v)
  lin <- if (view == "Bottom") bottom_measures(lance) else lateral_measures(lance, v)
  pheno <- lance[, c("ID", "species", "session")] %>% merge(scores, by = "ID") %>% merge(lin, by = "ID")
  write.csv(pheno, sprintf("PRIME_Lance%s_Pheno_v14.csv", view), row.names = FALSE)
  cat(sprintf("%s: %d individuals, %d landmarks, PC1-3 = %s%% of shape variance -> PRIME_Lance%s_Pheno_v14.csv\n",
              view, nrow(pheno), n_lm, paste(round(100 * lance_pca$d[1:3] / sum(lance_pca$d), 1), collapse = "/"), view))
  invisible(list(data = lance, gpa = lance_gpa, pca = lance_pca, pheno = pheno))
}

lance_right <- run_view("Right")
lance_left <- run_view("Left")
lance_bottom <- run_view("Bottom")

# e.g. species differences in blade length, controlling for imaging session:
# summary(lm(Ventral_arc_length_right ~ species + session, data = lance_right$pheno))
