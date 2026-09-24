############################################################################
# Random Forest: Can ovipositor SHAPE predict pine Host?
#
# Dataset: combined_g0_lec  (D. lecontei, G0/wild-collected generation only;
#          built by scripts/combined_landmark_analysis_v1.R)
#
# Question: is ovipositor shape sufficiently host-distinct that a classifier
#           trained only on shape variables can accurately predict which
#           pine Host an individual was collected from?
#
# Predictors: raw Procrustes-aligned landmark coordinates from gpagen()
#             (combined_lecontei_gpa$coords) -- i.e. the full GPA shape
#             variable set (32 landmarks x 2 dims = 64 variables), NOT the
#             PCA-reduced Comp1-15 scores. This retains 100% of shape
#             variance (no PC truncation) at the cost of higher
#             dimensionality and some collinearity among neighboring
#             landmarks.
#
# Approach:
#   1. Pull the GPA coordinates straight out of combined_lecontei_gpa and
#      match them to combined_g0_lec by ID (robust to any row reordering
#      introduced by merges elsewhere in the pipeline).
#   2. Check class balance across Host and drop hosts too small to classify.
#   3. Tune mtry with repeated stratified k-fold CV; evaluate on a held-out
#      stratified test split AND via OOB error on the full training set.
#   4. Run a label-permutation test so "accuracy" is judged against the
#      accuracy expected by chance for this exact class-size distribution
#      (NOT against 1/n_hosts, which is misleading when classes are uneven).
#   5. Variable importance -> which landmark coordinates (and, aggregated,
#      which landmarks) carry the host signal.
#   6. Optional class-balanced RF (downsampled per tree) as a robustness
#      check, since Host sample sizes are very likely uneven.
############################################################################

# ---- 0. Packages ---------------------------------------------------------
required_pkgs <- c("readxl", "dplyr", "geomorph", "ggplot2",
                    "randomForest", "caret")
missing_pkgs <- required_pkgs[!sapply(required_pkgs, requireNamespace, quietly = TRUE)]
if (length(missing_pkgs) > 0) install.packages(missing_pkgs)
invisible(lapply(required_pkgs, library, character.only = TRUE))

set.seed(42)  # reproducible CV folds, RF, and permutation test

# ---- 1. Get combined_g0_lec + the GPA object -------------------------------
# If this script is run fresh (not after combined_landmark_analysis_v1.R in
# the same session), source it to (re)build combined_g0_lec and
# combined_lecontei_gpa identically. Adjust the path below if this script is
# not run with the project root as the working directory.
if (!exists("combined_g0_lec") || !exists("combined_lecontei_gpa")) {
  source("scripts/combined_landmark_analysis_v1.R")
}

# ---- 2. Extract raw GPA (Procrustes-aligned) shape coordinates -------------
# two.d.array() flattens the gpagen() output (p x k x n array) back to an
# n x (p*k) matrix, in the same row order as combined_lecontei_pca_scores$ID
# (captured right after gpagen(), before any ID-sorting merges downstream).
lec_coords <- two.d.array(combined_lecontei_gpa$coords)
rownames(lec_coords) <- combined_lecontei_pca_scores$ID

coord_df <- as.data.frame(lec_coords)
colnames(coord_df) <- paste0("GPA_", colnames(coord_df))  # keep distinct from raw (non-aligned) X#/Y# columns
coord_df$ID <- combined_lecontei_pca_scores$ID

shape_vars <- setdiff(colnames(coord_df), "ID")
cat("GPA shape predictors:", length(shape_vars), "\n\n")

rf_data <- combined_g0_lec %>%
  select(ID, Host, Colony) %>%
  inner_join(coord_df, by = "ID") %>%
  filter(complete.cases(across(all_of(c("Host", shape_vars)))))

rf_data$Host <- factor(as.character(rf_data$Host))  # unordered, unused levels dropped

cat("Individuals available for RF:", nrow(rf_data), "\n")
cat("Rows dropped for missing Host/shape data:",
    nrow(combined_g0_lec) - nrow(rf_data), "\n\n")

# ---- 2a. Class balance check ----------------------------------------------
host_counts <- sort(table(rf_data$Host), decreasing = TRUE)
print(host_counts)

MIN_CLASS_N <- 5  # minimum individuals/host to attempt classification
keep_hosts <- names(host_counts[host_counts >= MIN_CLASS_N])
dropped_hosts <- setdiff(names(host_counts), keep_hosts)
if (length(dropped_hosts) > 0) {
  message("Dropping hosts with < ", MIN_CLASS_N, " individuals (too few to ",
          "split/cross-validate reliably): ", paste(dropped_hosts, collapse = ", "))
}

rf_data <- rf_data %>% filter(Host %in% keep_hosts)
rf_data$Host <- factor(as.character(rf_data$Host))
n_classes <- nlevels(rf_data$Host)
cat("\nHosts retained for RF (n =", n_classes, "):",
    paste(levels(rf_data$Host), collapse = ", "), "\n\n")

# ---- 3. Stratified train/test split ---------------------------------------
train_idx <- createDataPartition(rf_data$Host, p = 0.75, list = FALSE)
train_data <- rf_data[train_idx, ]
test_data  <- rf_data[-train_idx, ]

# ---- 4. Tune mtry with repeated stratified k-fold CV -----------------------
# number of folds capped by the smallest class in the training set so every
# fold still contains every class.
n_folds <- min(5, min(table(train_data$Host)))
ctrl <- trainControl(method = "repeatedcv", number = n_folds, repeats = 10,
                      classProbs = TRUE, savePredictions = "final")

# 64 raw coordinates make an exhaustive mtry sweep expensive -- spread ~8
# candidate values across the full range instead (includes the classic
# sqrt(p) heuristic within that range).
p <- length(shape_vars)
mtry_grid <- expand.grid(mtry = sort(unique(pmax(2, round(seq(2, p, length.out = 8))))))

rf_cv <- train(
  Host ~ .,
  data = train_data %>% select(Host, all_of(shape_vars)),
  method = "rf",
  trControl = ctrl,
  tuneGrid = mtry_grid,
  ntree = 1000,
  importance = TRUE
)

print(rf_cv)
best_mtry <- rf_cv$bestTune$mtry
cat("\nBest mtry:", best_mtry, "(of", p, "GPA coordinates)\n\n")

# cross-validated confusion matrix, pooled across held-out folds at best mtry
cv_preds <- rf_cv$pred[rf_cv$pred$mtry == best_mtry, ]
cv_cm <- confusionMatrix(cv_preds$pred, cv_preds$obs)
cat("---- Cross-validated (held-out folds) performance ----\n")
print(cv_cm)

# ---- 5. Final model + held-out test set evaluation --------------------------
final_rf <- randomForest(
  Host ~ ., data = train_data %>% select(Host, all_of(shape_vars)),
  mtry = best_mtry, ntree = 2000, importance = TRUE, proximity = TRUE
)

cat("\n---- OOB performance (training data) ----\n")
print(final_rf)

test_pred <- predict(final_rf, newdata = test_data)
test_cm <- confusionMatrix(test_pred, test_data$Host)
cat("\n---- Held-out test set performance ----\n")
print(test_cm)

# ---- 6. Permutation test: is accuracy > chance for THIS class distribution? -
# Shuffling Host labels preserves class sizes, giving a null distribution of
# accuracy attributable purely to guessing the majority/most-common classes --
# a much fairer baseline than 1/n_classes when Host sample sizes are uneven.
N_PERM <- 500  # raise to 999+ for a publication-grade p-value; slow to fit
obs_acc <- unname(test_cm$overall["Accuracy"])

perm_acc <- numeric(N_PERM)
pb <- txtProgressBar(min = 0, max = N_PERM, style = 3)
for (i in seq_len(N_PERM)) {
  perm_labels <- sample(train_data$Host)  # break the shape-Host association
  perm_rf <- randomForest(
    x = train_data %>% select(all_of(shape_vars)),
    y = perm_labels, mtry = best_mtry, ntree = 500
  )
  perm_pred <- predict(perm_rf, newdata = test_data %>% select(all_of(shape_vars)))
  perm_acc[i] <- mean(perm_pred == test_data$Host)
  setTxtProgressBar(pb, i)
}
close(pb)

perm_p <- (sum(perm_acc >= obs_acc) + 1) / (N_PERM + 1)

cat("\n---- Permutation test ----\n")
cat("Observed test accuracy:", round(obs_acc, 3), "\n")
cat("No-information rate (largest class):",
    round(unname(test_cm$overall["AccuracyNull"]), 3), "\n")
cat("Mean permuted accuracy:", round(mean(perm_acc), 3), "\n")
cat("Permutation p-value:", signif(perm_p, 3), "\n")

perm_df <- data.frame(Accuracy = perm_acc)
ggplot(perm_df, aes(x = Accuracy)) +
  geom_histogram(bins = 30, fill = "grey70", color = "white") +
  geom_vline(xintercept = obs_acc, color = "firebrick", linewidth = 1) +
  labs(title = "Permutation null distribution of classification accuracy",
       subtitle = paste0("Red line = observed accuracy (p = ", signif(perm_p, 3), ")"),
       x = "Accuracy on held-out test set", y = "Count") +
  theme_classic()

# ---- 7. Variable importance: which GPA coordinates carry the host signal? --
importance_df <- as.data.frame(importance(final_rf))
importance_df$Variable <- rownames(importance_df)
importance_df <- importance_df %>% arrange(desc(MeanDecreaseAccuracy))
print(importance_df)

ggplot(importance_df, aes(x = reorder(Variable, MeanDecreaseAccuracy), y = MeanDecreaseAccuracy)) +
  geom_col(fill = "steelblue") +
  coord_flip() +
  labs(title = "Variable importance: GPA coordinates discriminating Host",
       x = "Landmark coordinate", y = "Mean Decrease in Accuracy") +
  theme_classic()

# Aggregate to landmark-level importance (sum of its X + Y coordinate
# importance) for a more biologically interpretable summary than 64
# individual X/Y bars. Assumes two.d.array()'s default "X#"/"Y#" naming;
# falls back gracefully (skips) if that assumption doesn't hold.
landmark_num <- suppressWarnings(as.integer(gsub("^GPA_[XY]", "", importance_df$Variable)))
if (!anyNA(landmark_num)) {
  importance_df$Landmark <- landmark_num
  landmark_importance <- importance_df %>%
    group_by(Landmark) %>%
    summarise(MeanDecreaseAccuracy = sum(MeanDecreaseAccuracy), .groups = "drop") %>%
    arrange(desc(MeanDecreaseAccuracy))
  print(landmark_importance)

  ggplot(landmark_importance, aes(x = reorder(factor(Landmark), MeanDecreaseAccuracy),
                                   y = MeanDecreaseAccuracy)) +
    geom_col(fill = "darkorange") +
    coord_flip() +
    labs(title = "Landmark-level importance (X + Y combined)",
         x = "Landmark", y = "Summed Mean Decrease in Accuracy") +
    theme_classic()
}

# ---- 8. Class-balanced RF (robustness check for uneven Host sample sizes) --
class_sizes <- table(train_data$Host)
balanced_sampsize <- rep(min(class_sizes), length(class_sizes))
names(balanced_sampsize) <- names(class_sizes)

balanced_rf <- randomForest(
  Host ~ ., data = train_data %>% select(Host, all_of(shape_vars)),
  mtry = best_mtry, ntree = 2000, importance = TRUE,
  strata = train_data$Host, sampsize = balanced_sampsize
)

balanced_test_pred <- predict(balanced_rf, newdata = test_data)
balanced_test_cm <- confusionMatrix(balanced_test_pred, test_data$Host)
cat("\n---- Class-balanced RF: held-out test set performance ----\n")
print(balanced_test_cm)

# ---- 9. Diagnostics: OOB error convergence + proximity/MDS plot -----------
plot(final_rf, main = "OOB error rate vs. number of trees")

MDSplot(final_rf, train_data$Host,
        main = "RF proximity MDS: Host separation in shape space")

############################################################################
# OPTIONAL: use the Comp1-15 PCA shape scores instead of the full 64 raw GPA
# coordinates (fewer, decorrelated predictors; ~86% of shape variance).
# Uncomment to compare against the raw-coordinate results above.
############################################################################
# shape_pcs <- paste0("Comp", 1:15)
# rf_data_pcs <- combined_g0_lec %>%
#   select(ID, Host, all_of(shape_pcs)) %>%
#   filter(Host %in% keep_hosts, complete.cases(across(all_of(shape_pcs))))
# rf_data_pcs$Host <- factor(as.character(rf_data_pcs$Host))
# final_rf_pcs <- randomForest(Host ~ ., data = rf_data_pcs %>% select(-ID),
#                               importance = TRUE, ntree = 2000)
# print(final_rf_pcs)
