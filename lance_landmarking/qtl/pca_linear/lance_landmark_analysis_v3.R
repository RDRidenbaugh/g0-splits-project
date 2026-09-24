# previously: setwd("~/Academia/Ovipositor_QTL/LancePartyUSA/phenotype_genotype/pca_linear")
setwd("//wsl.localhost/Ubuntu/home/labradorite/g0-splits-project/lance_landmarking/qtl/pca_linear")

library(geomorph)
library(readxl)
lance_right <- read_excel("pca_cords_right_v3.xlsx")
lance_left <- read_excel("pca_cords_left_v3.xlsx")
lance_bottom <- read_excel("pca_cords_bottom_v3.xlsx")

lance_right$species <- factor(lance_right$species, levels = c("Lecontei", "LBX", "F1", "PBX", "Pinetum"))
lance_left$species <- factor(lance_left$species, levels = c("Lecontei", "LBX", "F1","PBX", "Pinetum"))
lance_bottom$species <- factor(lance_bottom$species, levels = c("Lecontei", "LBX", "F1","PBX", "Pinetum"))
lance_right[,3:143] <- sapply(lance_right[,3:143], as.numeric)
lance_left[,3:127] <- sapply(lance_left[,3:127], as.numeric)
lance_bottom[,3:67] <- sapply(lance_bottom[,3:67], as.numeric)

## Linear Measurements
library(dplyr)
# Length of the Cuticular Window (Cutwindow_length_right)
lance_right <- mutate(lance_right, Cutwindow_length_right = sqrt(((lance_right$X25-lance_right$X14)^2)+((lance_right$Y25-lance_right$Y14)^2)))
lance_right <- mutate(lance_right, Sut1_length_right = sqrt(((lance_right$X14-lance_right$X4)^2+(lance_right$Y14-lance_right$Y4)^2)))
lance_right <- mutate(lance_right, Sut2_length_right = sqrt(((lance_right$X15-lance_right$X5)^2+(lance_right$Y15-lance_right$Y5)^2)))
lance_right <- mutate(lance_right, Sut3_length_right = sqrt(((lance_right$X17-lance_right$X6)^2+(lance_right$Y17-lance_right$Y6)^2)))
lance_right <- mutate(lance_right, Sut4_length_right = sqrt(((lance_right$X19-lance_right$X7)^2+(lance_right$Y19-lance_right$Y7)^2)))
lance_right <- mutate(lance_right, Sut5_length_right = sqrt(((lance_right$X21-lance_right$X8)^2+(lance_right$Y21-lance_right$Y8)^2)))
lance_right <- mutate(lance_right, Sut6_length_right = sqrt(((lance_right$X23-lance_right$X9)^2+(lance_right$Y23-lance_right$Y9)^2)))
lance_right <- mutate(lance_right, Arc1_width_right = sqrt(((lance_right$X5-lance_right$X4)^2+(lance_right$Y5-lance_right$Y4)^2)))
lance_right <- mutate(lance_right, Arc2_width_right = sqrt(((lance_right$X6-lance_right$X5)^2+(lance_right$Y6-lance_right$Y5)^2)))
lance_right <- mutate(lance_right, Arc3_width_right = sqrt(((lance_right$X7-lance_right$X6)^2+(lance_right$Y7-lance_right$Y6)^2)))
lance_right <- mutate(lance_right, Arc4_width_right = sqrt(((lance_right$X8-lance_right$X7)^2+(lance_right$Y8-lance_right$Y7)^2)))
lance_right <- mutate(lance_right, Arc5_width_right = sqrt(((lance_right$X9-lance_right$X8)^2+(lance_right$Y9-lance_right$Y8)^2)))
lance_right <- mutate(lance_right, Arc6_width_right = sqrt(((lance_right$X10-lance_right$X9)^2+(lance_right$Y10-lance_right$Y9)^2)))
lance_right <- mutate(lance_right, Rightface_len = sqrt(((lance_right$X13-lance_right$X1)^2+(lance_right$Y13-lance_right$Y1)^2)))
lance_right <- mutate(lance_right, cut_edge_length = sqrt(((lance_right$X13-lance_right$X11)^2+(lance_right$Y13-lance_right$Y11)^2)))
lance_right <- mutate(lance_right, window_to_edge1 = sqrt(((lance_right$X25-lance_right$X13)^2+(lance_right$Y25-lance_right$Y13)^2)))
lance_right <- mutate(lance_right, window_to_edge2 = sqrt(((lance_right$X25-lance_right$X12)^2+(lance_right$Y25-lance_right$Y12)^2)))
lance_right <- mutate(lance_right, Intersect_to_top_dist_right = sqrt(((lance_right$X30-lance_right$X29)^2+(lance_right$Y30-lance_right$Y29)^2)))
lance_right <- mutate(lance_right, dist_arc2_arc3_right = sqrt(((lance_right$X18-lance_right$X16)^2+(lance_right$Y18-lance_right$Y16)^2)))
lance_right <- mutate(lance_right, dist_arc3_arc4_right = sqrt(((lance_right$X20-lance_right$X18)^2+(lance_right$Y20-lance_right$Y18)^2)))
lance_right <- mutate(lance_right, dist_arc4_arc5_right = sqrt(((lance_right$X22-lance_right$X20)^2+(lance_right$Y22-lance_right$Y20)^2)))
lance_right <- mutate(lance_right, Rightface_height1 = sqrt(((lance_right$X36-lance_right$X10)^2+(lance_right$Y36-lance_right$Y10)^2)))
lance_right <- mutate(lance_right, Rightface_height2 = sqrt(((lance_right$X35-lance_right$X8)^2+(lance_right$Y35-lance_right$Y8)^2)))
lance_right <- mutate(lance_right, Rightface_height3 = sqrt(((lance_right$X34-lance_right$X7)^2+(lance_right$Y34-lance_right$Y7)^2)))
lance_right <- mutate(lance_right, Rightface_height4 = sqrt(((lance_right$X33-lance_right$X6)^2+(lance_right$Y33-lance_right$Y6)^2)))
lance_right <- mutate(lance_right, Rightface_height5 = sqrt(((lance_right$X32-lance_right$X5)^2+(lance_right$Y32-lance_right$Y5)^2)))
lance_right <- mutate(lance_right, Rightface_height6 = sqrt(((lance_right$X31-lance_right$X4)^2+(lance_right$Y31-lance_right$Y4)^2)))
lance_right <- mutate(lance_right, Rightface_height7 = sqrt(((lance_right$X30-lance_right$X3)^2+(lance_right$Y30-lance_right$Y3)^2)))
lance_right <- mutate(lance_right, cutting_depth1 = sqrt(((lance_right$X28-lance_right$X13)^2+(lance_right$Y28-lance_right$Y13)^2)))
lance_right <- mutate(lance_right, cutting_depth2 = sqrt(((lance_right$X27-lance_right$X12)^2+(lance_right$Y27-lance_right$Y12)^2)))
lance_right <- mutate(lance_right, rail_length = sqrt(((lance_right$X30-lance_right$X28)^2+(lance_right$Y30-lance_right$Y28)^2)))
lance_right <- mutate(lance_right, window_to_rail = sqrt(((lance_right$X35-lance_right$X21)^2+(lance_right$Y35-lance_right$Y21)^2)))
#write.csv(lance_right,"PRIME_LanceRight_Pheno_v3.csv", row.names = FALSE)

#linear measure calculations left side
lance_left <- mutate(lance_left, Cutwindow_length_left = sqrt(((lance_left$X24-lance_left$X14)^2+(lance_left$Y24-lance_left$Y14)^2)))
lance_left <- mutate(lance_left, Sut1_length_left = sqrt(((lance_left$X14-lance_left$X4)^2+(lance_left$Y14-lance_left$Y4)^2)))
lance_left <- mutate(lance_left, Sut2_length_left = sqrt(((lance_left$X15-lance_left$X5)^2+(lance_left$Y15-lance_left$Y5)^2)))
lance_left <- mutate(lance_left, Sut3_length_left = sqrt(((lance_left$X17-lance_left$X6)^2+(lance_left$Y17-lance_left$Y6)^2)))
lance_left <- mutate(lance_left, Sut4_length_left = sqrt(((lance_left$X19-lance_left$X7)^2+(lance_left$Y19-lance_left$Y7)^2)))
lance_left <- mutate(lance_left, Sut5_length_left = sqrt(((lance_left$X21-lance_left$X8)^2+(lance_left$Y21-lance_left$Y8)^2)))
lance_left <- mutate(lance_left, Sut6_length_left = sqrt(((lance_left$X23-lance_left$X9)^2+(lance_left$Y23-lance_left$Y9)^2)))
lance_left <- mutate(lance_left, Arc1_width_left = sqrt(((lance_left$X5-lance_left$X4)^2+(lance_left$Y5-lance_left$Y4)^2)))
lance_left <- mutate(lance_left, Arc2_width_left = sqrt(((lance_left$X6-lance_left$X5)^2+(lance_left$Y6-lance_left$Y5)^2)))
lance_left <- mutate(lance_left, Arc3_width_left = sqrt(((lance_left$X7-lance_left$X6)^2+(lance_left$Y7-lance_left$Y6)^2)))
lance_left <- mutate(lance_left, Arc4_width_left = sqrt(((lance_left$X8-lance_left$X7)^2+(lance_left$Y8-lance_left$Y7)^2)))
lance_left <- mutate(lance_left, Arc5_width_left = sqrt(((lance_left$X9-lance_left$X8)^2+(lance_left$Y9-lance_left$Y8)^2)))
lance_left <- mutate(lance_left, Leftface_length = sqrt(((lance_left$X13-lance_left$X1)^2+(lance_left$Y13-lance_left$Y1)^2)))
lance_left <- mutate(lance_left, noncut_edge_length = sqrt(((lance_left$X13-lance_left$X10)^2+(lance_left$Y13-lance_left$Y10)^2)))
lance_left <- mutate(lance_left, Intersect_to_top_dist_left = (((lance_left$X26-lance_left$X25)^2+(lance_left$X26-lance_left$X25)^2)))
lance_left <- mutate(lance_left, dist_arc2_arc3_left = sqrt(((lance_left$X18-lance_left$X16)^2+(lance_left$Y18-lance_left$Y16)^2)))
lance_left <- mutate(lance_left, dist_arc3_arc4_left = sqrt(((lance_left$X20-lance_left$X18)^2+(lance_left$Y20-lance_left$Y18)^2)))
lance_left <- mutate(lance_left, dist_arc4_arc5_left = sqrt(((lance_left$X22-lance_left$X20)^2+(lance_left$Y22-lance_left$Y20)^2)))
lance_left <- mutate(lance_left, Leftface_height1 = sqrt(((lance_left$X32-lance_left$X9)^2+(lance_left$Y32-lance_left$Y9)^2)))
lance_left <- mutate(lance_left, Leftface_height2 = sqrt(((lance_left$X31-lance_left$X8)^2+(lance_left$Y31-lance_left$Y8)^2)))
lance_left <- mutate(lance_left, Leftface_height3 = sqrt(((lance_left$X30-lance_left$X7)^2+(lance_left$Y30-lance_left$Y7)^2)))
lance_left <- mutate(lance_left, Leftface_height4 = sqrt(((lance_left$X29-lance_left$X6)^2+(lance_left$Y29-lance_left$Y6)^2)))
lance_left <- mutate(lance_left, Leftface_height5 = sqrt(((lance_left$X28-lance_left$X5)^2+(lance_left$Y28-lance_left$Y5)^2)))
lance_left <- mutate(lance_left, Leftface_height6 = sqrt(((lance_left$X27-lance_left$X4)^2+(lance_left$Y27-lance_left$Y4)^2)))
lance_left <- mutate(lance_left, Leftface_height7 = sqrt(((lance_left$X26-lance_left$Y3)^2+(lance_left$Y26-lance_left$Y3)^2)))
#write.csv(lance_left,"PRIME_LanceLeft_Pheno_v3.csv", row.names = FALSE)

#linear measure calculations bottom
lance_bottom<- mutate(lance_bottom, cut_edge_length_bot = sqrt(((lance_bottom$X6-lance_bottom$X1)^2+(lance_bottom$Y6-lance_bottom$Y1)^2)))
lance_bottom<- mutate(lance_bottom, noncut_edge_length_bot1 = sqrt(((lance_bottom$X13-lance_bottom$X12)^2+(lance_bottom$Y13-lance_bottom$Y12)^2)))
lance_bottom<- mutate(lance_bottom, noncut_edge_length_bot2 = sqrt(((lance_bottom$X13-lance_bottom$X6)^2+(lance_bottom$Y13-lance_bottom$Y6)^2)))
lance_bottom<- mutate(lance_bottom, distance_to_tip = sqrt(((lance_bottom$X13-lance_bottom$X1)^2+(lance_bottom$Y13-lance_bottom$Y1)^2)))
lance_bottom<- mutate(lance_bottom, inner_angle = ((180/pi)*(acos(((cut_edge_length_bot^2)+(noncut_edge_length_bot2^2)-(distance_to_tip^2))/(2*(cut_edge_length_bot*noncut_edge_length_bot2))))))
lance_bottom<- mutate(lance_bottom, left_width_sut8 = sqrt(((lance_bottom$X14-lance_bottom$X11)^2+(lance_bottom$Y14-lance_bottom$Y11)^2)))
lance_bottom<- mutate(lance_bottom, left_width_sut7 = sqrt(((lance_bottom$X15-lance_bottom$X10)^2+(lance_bottom$Y15-lance_bottom$Y10)^2)))
lance_bottom<- mutate(lance_bottom, right_width_sut8 = sqrt(((lance_bottom$X7-lance_bottom$X2)^2+(lance_bottom$Y7-lance_bottom$Y2)^2)))
lance_bottom<- mutate(lance_bottom, right_width_sut7 = sqrt(((lance_bottom$X8-lance_bottom$X3)^2+(lance_bottom$Y8-lance_bottom$Y3)^2)))
lance_bottom<- mutate(lance_bottom, bottom_width = sqrt(((lance_bottom$X14-lance_bottom$X2)^2+(lance_bottom$Y14-lance_bottom$Y2)^2)))
#write.csv(lance_bottom,"PRIME_LanceBottom_Pheno_v3.csv", row.names = FALSE)

## Models
library(car)
library(emmeans)
# Right
# PCAs
model1_right <-lm(lance_right$Comp1~lance_right$species)
Anova(model1_right,type=2) # 2.2e-16 ***
emmeans(model1_right, pairwise~species, adjust="fdr")

model2_right <-lm(lance_right$Comp2~lance_right$species)
Anova(model2_right,type=2) # n.s.
emmeans(model2_right, pairwise~species, adjust="fdr")

model3_right <-lm(lance_right$Comp3~lance_right$species)
Anova(model3_right,type=2) # 2.127e-11 ***
emmeans(model3_right, pairwise~species, adjust="fdr")

model4_right <-lm(lance_right$Comp4~lance_right$species)
Anova(model4_right,type=2) # n.s.
emmeans(model4_right, pairwise~species, adjust="fdr")

model5_right <-lm(lance_right$Comp5~lance_right$species)
Anova(model5_right,type=2) # 2.038e-05 ***
emmeans(model5_right, pairwise~species, adjust="fdr")

model6_right <-lm(lance_right$Comp6~lance_right$species)
Anova(model6_right,type=2) # n.s.
emmeans(model6_right, pairwise~species, adjust="fdr")

model7_right <-lm(lance_right$Comp7~lance_right$species)
Anova(model7_right,type=2) # 2.904e-06 ***
emmeans(model7_right, pairwise~species, adjust="fdr")

model8_right <-lm(lance_right$Comp8~lance_right$species)
Anova(model8_right,type=2) # n.s.
emmeans(model8_right, pairwise~species, adjust="fdr")

model9_right <-lm(lance_right$Comp9~lance_right$species)
Anova(model9_right,type=2) # 0.0006849 ***
emmeans(model9_right, pairwise~species, adjust="fdr")

model10_right <-lm(lance_right$Comp10~lance_right$species)
Anova(model10_right,type=2) # 0.0006849 ***
emmeans(model10_right, pairwise~species, adjust="fdr")

model11_right <-lm(lance_right$Comp11~lance_right$species)
Anova(model11_right,type=2) # 1.372e-08 ***
emmeans(model11_right, pairwise~species, adjust="fdr")

model12_right <-lm(lance_right$Comp12~lance_right$species)
Anova(model12_right,type=2) # 2.241e-05 ***
emmeans(model12_right, pairwise~species, adjust="fdr")


model13_right <-lm(lance_right$centroid_size_right~lance_right$species)
Anova(model1_right,type=2) # 2.2e-16 ***
emmeans(model3_right, pairwise~species, adjust="fdr")

# Linear
model14_right <-lm(data = lance_right, Cutwindow_length_right ~ species)
Anova(model14_right,type=2) # 2.2e-16 ***
emmeans(model14_right, pairwise~species, adjust="fdr")

model15_right <-lm(data = lance_right, Sut1_length_right ~ species)
Anova(model15_right,type=2) # 2.2e-16 ***
emmeans(model15_right, pairwise~species, adjust="fdr")

model16_right <-lm(data = lance_right, Sut2_length_right ~ species)
Anova(model16_right,type=2) # 2.2e-16 ***
emmeans(model16_right, pairwise~species, adjust="fdr")

model17_right <-lm(data = lance_right, Sut3_length_right ~ species)
Anova(model17_right,type=2) # 2.2e-16 ***
emmeans(model17_right, pairwise~species, adjust="fdr")

model18_right <-lm(data = lance_right, Sut4_length_right ~ species)
Anova(model18_right,type=2) # 2.2e-16 ***
emmeans(model18_right, pairwise~species, adjust="fdr")

model19_right <-lm(data = lance_right, Sut5_length_right ~ species)
Anova(model19_right,type=2) # 1.508e-07 ***
emmeans(model19_right, pairwise~species, adjust="fdr")

model20_right <-lm(data = lance_right, Sut6_length_right ~ species)
Anova(model120_right,type=2) # 1.051e-07 ***
emmeans(model120_right, pairwise~species, adjust="fdr")

model21_right <-lm(data = lance_right, Rightface_len ~ species)
Anova(model21_right,type=2) # 2.2e-16 ***
emmeans(model21_right, pairwise~species, adjust="fdr")

model22_right <-lm(data = lance_right, cut_edge_length ~ species)
Anova(model22_right,type=2)
emmeans(model22_right, pairwise~species, adjust="fdr")

model23a_right <-lm(data = lance_right, window_to_edge1 ~ species)
Anova(model23a_right,type=2)
emmeans(model23a_right, pairwise~species, adjust="fdr")

model23b_right <-lm(data = lance_right, window_to_edge2 ~ species)
Anova(model23b_right,type=2)
emmeans(model23b_right, pairwise~species, adjust="fdr") 

model24_right <-lm(data = lance_right, Rightface_height1 ~ species)
Anova(model24_right,type=2)
emmeans(model24_right, pairwise~species, adjust="fdr")

model25_right <-lm(data = lance_right, Rightface_height6 ~ species)
Anova(model25_right,type=2)
emmeans(model25_right, pairwise~species, adjust="fdr")

model26_right <-lm(data = lance_right, cutting_depth1 ~ species)
Anova(model26_right,type=2)
emmeans(model26_right, pairwise~species, adjust="fdr")

model27_right <-lm(data = lance_right, cutting_depth2 ~ species)
Anova(model27_right,type=2)
emmeans(model27_right, pairwise~species, adjust="fdr")

model28_right <-lm(data = lance_right, rail_length ~ species)
Anova(model28_right,type=2)
emmeans(model28_right, pairwise~species, adjust="fdr")

model29_right <-lm(data = lance_right, window_to_rail ~ species)
Anova(model29_right,type=2)
emmeans(model29_right, pairwise~species, adjust="fdr")

# Left
# PCAs
model1_left <-lm(lance_left$Comp1~lance_left$species)
Anova(model1_left,type=2) # < 2.2e-16 ***
emmeans(model1_left, pairwise~species, adjust="fdr")

model2_left <-lm(lance_left$Comp2~lance_left$species) 
Anova(model2_left,type=2) # 3.131e-12 ***
emmeans(model2_left, pairwise~species, adjust="fdr")

model3_left <-lm(lance_left$Comp3~lance_left$species) 
Anova(model3_left,type=2) # 1.176e-13 ***
emmeans(model3_left, pairwise~species, adjust="fdr")

model4_left <-lm(lance_left$Comp4~lance_left$species) 
Anova(model4_left,type=2) # < 2.2e-16 ***
emmeans(model4_left, pairwise~species, adjust="fdr")

model5_left <-lm(lance_left$Comp5~lance_left$species) 
Anova(model5_left,type=2) # 3.416e-06 ***
emmeans(model5_left, pairwise~species, adjust="fdr")

model6_left <-lm(lance_left$Comp6~lance_left$species) 
Anova(model6_left,type=2) # 1.955e-05 ***
emmeans(model6_left, pairwise~species, adjust="fdr")

model7_left <-lm(lance_left$Comp7~lance_left$species) 
Anova(model7_left,type=2) # 9.124e-05 ***
emmeans(model7_left, pairwise~species, adjust="fdr")

model8_left <-lm(lance_left$Comp8~lance_left$species) 
Anova(model8_left,type=2) # 0.0003714 ***
emmeans(model8_left, pairwise~species, adjust="fdr")

model9_left <-lm(lance_left$Comp9~lance_left$species) 
Anova(model9_left,type=2) # n.s.
emmeans(model9_left, pairwise~species, adjust="fdr")

model10_left <-lm(lance_left$Comp10~lance_left$species) 
Anova(model10_left,type=2) # n.s.
emmeans(model10_left, pairwise~species, adjust="fdr")

model11_left <-lm(lance_left$Comp11~lance_left$species) 
Anova(model11_left,type=2) # 1.805e-05 ***
emmeans(model11_left, pairwise~species, adjust="fdr")

model12_left <-lm(lance_left$Comp12~lance_left$species) 
Anova(model12_left,type=2) # 0.0001837 ***
emmeans(model12_left, pairwise~species, adjust="fdr")

model13_left <-lm(lance_left$centroid_size_left~lance_left$species)
Anova(model13_left,type=2) # 2.2e-16 ***
emmeans(model13_left, pairwise~species, adjust="fdr")

# Bottom
# PCAs
model1_bottom <-lm(lance_bottom$Comp1~lance_bottom$species)
Anova(model1_bottom,type=2) # < 2.2e-16 ***
emmeans(model1_bottom, pairwise~species, adjust="fdr")

model2_bottom <-lm(lance_bottom$Comp2~lance_bottom$species) 
Anova(model2_bottom,type=2) # < 2.2e-16 ***
emmeans(model2_bottom, pairwise~species, adjust="fdr")

model3_bottom <-lm(lance_bottom$Comp3~lance_bottom$species) 
Anova(model3_bottom,type=2) # 2.174e-12 ***
emmeans(model3_bottom, pairwise~species, adjust="fdr")

model4_bottom <-lm(lance_bottom$Comp4~lance_bottom$species) 
Anova(model4_bottom,type=2) # < 2.2e-16 ***
emmeans(model4_bottom, pairwise~species, adjust="fdr")

model5_bottom <-lm(lance_bottom$Comp5~lance_bottom$species) 
Anova(model5_bottom,type=2) # 2.517e-12 ***
emmeans(model5_bottom, pairwise~species, adjust="fdr")

model6_bottom <-lm(lance_bottom$Comp6~lance_bottom$species) 
Anova(model6_bottom,type=2) # 3.134e-08 ***
emmeans(model6_bottom, pairwise~species, adjust="fdr")

model7_bottom <-lm(lance_bottom$Comp7~lance_bottom$species) 
Anova(model7_bottom,type=2) # 1.655e-08 ***
emmeans(model7_bottom, pairwise~species, adjust="fdr")

model8_bottom <-lm(lance_bottom$Comp8~lance_bottom$species) 
Anova(model8_bottom,type=2) # n.s.
emmeans(model8_bottom, pairwise~species, adjust="fdr")

model9_bottom <-lm(lance_bottom$Comp9~lance_bottom$species) 
Anova(model9_bottom,type=2) # 0.004656 **
emmeans(model9_bottom, pairwise~species, adjust="fdr")

model10_bottom <-lm(lance_bottom$Comp10~lance_bottom$species) 
Anova(model10_bottom,type=2) # n.s.
emmeans(model10_bottom, pairwise~species, adjust="fdr")

model11_bottom <-lm(lance_bottom$Comp11~lance_bottom$species) 
Anova(model11_bottom,type=2) # n.s.
emmeans(model11_bottom, pairwise~species, adjust="fdr")

model12_bottom <-lm(lance_bottom$Comp12~lance_bottom$species) 
Anova(model12_bottom,type=2) # n.s.
emmeans(model12_bottom, pairwise~species, adjust="fdr")

model13_bottom <-lm(lance_bottom$centroid_size_bottom~lance_bottom$species)
Anova(model13_bottom,type=2) # < 2.2e-16 ***
emmeans(model13_bottom, pairwise~species, adjust="fdr")

## Figures
library(ggplot2)
library(MetBrewer)
# Right
PC1vPC2_right <- ggplot(data = lance_right, aes(Comp1, Comp2, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC1vPC2_right)

PC3vPC4_right <- ggplot(data = lance_right, aes(Comp3, Comp4, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC3vPC4_right)

PC5vPC6_right <- ggplot(data = lance_right, aes(Comp5, Comp6, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC5vPC6_right)

PC7vPC8_right <- ggplot(data = lance_right, aes(Comp7, Comp8, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC7vPC8_right)

CentvPC1_right <- ggplot(data = lance_right, aes(Comp1, centroid_size_right, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(CentvPC1_right)

cut_edge_right <- ggplot(data = lance_right, aes(species, cut_edge_length, fill = species)) +
  geom_boxplot() +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(cut_edge_right)

window_to_edge1_right <- ggplot(data = lance_right, aes(species, window_to_edge1, fill = species)) +
  geom_boxplot() +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(window_to_edge1_right)

Rightface_height1_right <- ggplot(data = lance_right, aes(species, Rightface_height1, fill = species)) +
  geom_boxplot() +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(Rightface_height1_right)

Rightface_height6_right <- ggplot(data = lance_right, aes(species, Rightface_height6, fill = species)) +
  geom_boxplot() +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(Rightface_height6_right)


# Left
PC1vPC2_left <- ggplot(data = lance_left, aes(Comp1, Comp2, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC1vPC2_left)

PC3vPC4_left <- ggplot(data = lance_left, aes(Comp3, Comp4, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC3vPC4_left)

PC5vPC6_left <- ggplot(data = lance_left, aes(Comp5, Comp6, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC5vPC6_left)

PC7vPC8_left <- ggplot(data = lance_left, aes(Comp7, Comp8, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC7vPC8_left)

CentvPC1_left <- ggplot(data = lance_left, aes(Comp1, centroid_size_left, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(CentvPC1_left)

# Bottom
# PCAs
PC1vPC2_bottom <- ggplot(data = lance_bottom, aes(Comp1, Comp2, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC1vPC2_bottom)

PC3vPC4_bottom <- ggplot(data = lance_bottom, aes(Comp3, Comp4, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC3vPC4_bottom)

PC5vPC6_bottom <- ggplot(data = lance_bottom, aes(Comp5, Comp6, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC5vPC6_bottom)

PC7vPC8_bottom <- ggplot(data = lance_bottom, aes(Comp7, Comp8, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(PC7vPC8_bottom)

CentvPC1_left <- ggplot(data = lance_left, aes(Comp1, centroid_size_left, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(CentvPC1_left)

CentvPC1_bottom <- ggplot(data = lance_bottom, aes(Comp1, centroid_size_bottom, Comp1, fill = species)) +
  geom_point(size = 4, shape = 21) +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(CentvPC1_bottom)

# Linear
InnerAngle_bottom <- ggplot(data = lance_bottom, aes(species, inner_angle, Comp1, fill = species)) +
  geom_boxplot() +
  scale_fill_manual(values = met.brewer("OKeeffe1", 5))
print(InnerAngle_bottom)