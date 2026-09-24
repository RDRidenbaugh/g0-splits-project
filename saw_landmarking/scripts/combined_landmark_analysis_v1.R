library(readxl)
library(dplyr)
library(geomorph)
library(ggplot2)

setwd("//wsl.localhost/Ubuntu/home/labradorite/g0-splits-project/saw_landmarking")  # data moved into saw_landmarking/ (2026-09-24 reorganization)

# Loading G0 Data set
g0_all <- read_excel("PRIME_Compiled_G0_PhenoXY_v6.xlsx", na = "NA")
g0_all <- filter(g0_all, ID != "RB462_F3" & ID != "087_04_F1") #Outliers
g0_all$Host <- as.factor(g0_all$Host)
g0_all$Treatment <- as.factor(g0_all$Treatment)
g0_all$Species <- as.factor(g0_all$Species)
g0_all$Population <- as.factor(g0_all$Population)
g0_all$DNA <- as.factor(g0_all$DNA)

# Loading Splits Data set
splits_all <- read_excel("PRIME_Compiled_Splits_PhenoXY_v8.xlsx", na = "NA")
splits_all <- filter(splits_all, ID != "NL22NE_X012_A9") # Centroid Outlier
splits_all$Treatment <- as.factor(splits_all$Treatment)
splits_all$Species <- as.factor(splits_all$Species)

# Merging Data sets
combined_all <- full_join(g0_all, splits_all)
combined_all$Host <- ordered(combined_all$Host, levels = c("white", "spruce", "dwarf_mountain", "scots", "shortleaf", "loblolly", "virginia","red", "pitch", "slash", "longleaf", "jack", "austrian"))

# Calculating Linear Measurements
combined_all$TopLengthLM<-sqrt(((combined_all$X32-combined_all$X25)^2)+((combined_all$Y32-combined_all$Y25)^2))
combined_all$RootTipLM<-sqrt(((combined_all$X25-combined_all$X15)^2)+((combined_all$Y25-combined_all$Y15)^2))
combined_all$BottomLengthLM<-sqrt(((combined_all$X15-combined_all$X1)^2)+((combined_all$Y15-combined_all$Y1)^2))
combined_all$Ann1LM<-sqrt(((combined_all$X25-combined_all$X1)^2)+((combined_all$Y25-combined_all$Y1)^2))
combined_all$Ann2LM<-sqrt(((combined_all$X26-combined_all$X2)^2)+((combined_all$Y26-combined_all$Y2)^2))
combined_all$Ann3LM<-sqrt(((combined_all$X27-combined_all$X5)^2)+((combined_all$Y27-combined_all$Y5)^2))
combined_all$Ann4LM<-sqrt(((combined_all$X28-combined_all$X8)^2)+((combined_all$Y28-combined_all$Y8)^2))
combined_all$Ann5LM<-sqrt(((combined_all$X29-combined_all$X10)^2)+((combined_all$Y29-combined_all$Y10)^2))
combined_all$Ann6LM<-sqrt(((combined_all$X30-combined_all$X11)^2)+((combined_all$Y30-combined_all$Y11)^2))
combined_all$Ann7LM<-sqrt(((combined_all$X31-combined_all$X12)^2)+((combined_all$Y31-combined_all$Y12)^2))
combined_all$Ann8LM<-sqrt(((combined_all$X32-combined_all$X13)^2)+((combined_all$Y32-combined_all$Y13)^2))
combined_all$Tooth1LM<-sqrt(((combined_all$X3-combined_all$X2)^2)+((combined_all$Y3-combined_all$Y2)^2))
combined_all$Tooth2LM<-sqrt(((combined_all$X6-combined_all$X5)^2)+((combined_all$Y6-combined_all$Y5)^2))
combined_all$Tooth3LM<-sqrt(((combined_all$X9-combined_all$X8)^2)+((combined_all$Y9-combined_all$Y8)^2))
combined_all$DistAnn1_2topLM<-sqrt(((combined_all$X17-combined_all$X16)^2)+((combined_all$Y17-combined_all$Y16)^2))
combined_all$DistAnn2_3topLM<-sqrt(((combined_all$X18-combined_all$X17)^2)+((combined_all$Y18-combined_all$Y17)^2))
combined_all$DistAnn3_4topLM<-sqrt(((combined_all$X19-combined_all$X18)^2)+((combined_all$Y19-combined_all$Y18)^2))
combined_all$DistAnn4_5topLM<-sqrt(((combined_all$X20-combined_all$X19)^2)+((combined_all$Y20-combined_all$Y19)^2))
combined_all$DistAnn5_6topLM<-sqrt(((combined_all$X21-combined_all$X20)^2)+((combined_all$Y21-combined_all$Y20)^2))
combined_all$DistAnn6_7topLM<-sqrt(((combined_all$X22-combined_all$X21)^2)+((combined_all$Y22-combined_all$Y21)^2))
combined_all$DistAnn7_tiptopLM<-sqrt(((combined_all$X22-combined_all$X15)^2)+((combined_all$Y22-combined_all$Y15)^2))
combined_all$DistAnn1_2botLM<-sqrt(((combined_all$X2-combined_all$X1)^2)+((combined_all$Y2-combined_all$Y1)^2))
combined_all$DistAnn2_3botLM<-sqrt(((combined_all$X5-combined_all$X2)^2)+((combined_all$Y5-combined_all$Y2)^2))
combined_all$DistAnn3_4botLM<-sqrt(((combined_all$X8-combined_all$X5)^2)+((combined_all$Y8-combined_all$Y5)^2))
combined_all$DistAnn4_5botLM<-sqrt(((combined_all$X10-combined_all$X8)^2)+((combined_all$Y10-combined_all$Y8)^2))
combined_all$DistAnn5_6botLM<-sqrt(((combined_all$X11-combined_all$X10)^2)+((combined_all$Y11-combined_all$Y10)^2))
combined_all$DistAnn6_7botLM<-sqrt(((combined_all$X12-combined_all$X11)^2)+((combined_all$Y12-combined_all$Y11)^2))
combined_all$DistAnn7_8botLM<-sqrt(((combined_all$X13-combined_all$X12)^2)+((combined_all$Y13-combined_all$Y12)^2))
combined_all$DistAnn8_9botLM<-sqrt(((combined_all$X14-combined_all$X13)^2)+((combined_all$Y14-combined_all$Y13)^2))
combined_all$DistAnn9_tipbotLM<-sqrt(((combined_all$X15-combined_all$X14)^2)+((combined_all$Y15-combined_all$Y14)^2))

# Subsetting Species
combined_lecontei <- combined_all %>% subset(combined_all$Species != "PINETUM")
combined_pinetum <- combined_all %>% subset(combined_all$Species != "LECONTEI")

# Computing combined_all shape gpa
ID <- combined_all[,1]
combined_all_array <- arrayspecs(combined_all[,18:81], 32, 2) 
mode(combined_all_array) <- "numeric"
combined_all_gpa <- gpagen(combined_all_array, ProcD=F)
combined_all_pca<-gm.prcomp(combined_all_gpa$coords)
combined_all_eig <- combined_all_pca$d
combined_all_percent_var <- (combined_all_eig  / sum(combined_all_eig )) * 100
temp_df <- data.frame(PC = 1:length(combined_all_percent_var), Variance = combined_all_percent_var)
ggplot(temp_df, aes(x = PC, y = Variance)) +
  geom_point() +
  geom_line() +
  scale_x_continuous(breaks = seq(0, 60, by=5)) +
  labs(title = "combined_all Scree Plot", x = "Principal Component", y = "Proportion of Variance Explained") +
  theme_minimal()
sum(combined_all_percent_var[1:5]) # 88.24% explained in first 5 PCs
all_pca_scores<-combined_all_pca$x
all_centroid_size<-combined_all_gpa$Csize
combined_all_pca_scores<-cbind.data.frame(ID,all_centroid_size,all_pca_scores)
combined_all <- merge(x= combined_all, y=combined_all_pca_scores[,1:7], by = "ID") #Retaining Centroid + Comp1-5

combined_g0_all <- combined_all %>% subset(combined_all$Treatment == "W")
combined_g0_all$Treatment <- factor(combined_g0_all$Treatment)
combined_g0_all$Host <- factor(combined_g0_all$Host)

combined_splits_all <- combined_all %>% subset(combined_all$Treatment != "W")
combined_splits_all$Treatment <- factor(combined_splits_all$Treatment)
combined_splits_all$Host <- factor(combined_splits_all$Host)

# Computing combined_lecontei shape gpa
ID <- combined_lecontei[,1]
combined_lecontei_array <- arrayspecs(combined_lecontei[,18:81], 32, 2) 
mode(combined_lecontei_array) <- "numeric"
combined_lecontei_gpa <- gpagen(combined_lecontei_array, ProcD=F)
combined_lecontei_pca<-gm.prcomp(combined_lecontei_gpa$coords)
combined_lecontei_eig <- combined_lecontei_pca$d
combined_lecontei_percent_var <- (combined_lecontei_eig  / sum(combined_lecontei_eig )) * 100
temp_df <- data.frame(PC = 1:length(combined_lecontei_percent_var), Variance = combined_lecontei_percent_var)
ggplot(temp_df, aes(x = PC, y = Variance)) +
  geom_point() +
  geom_line() +
  scale_x_continuous(breaks = seq(0, 60, by=5)) +
  labs(title = "combined_lecontei Scree Plot", x = "Principal Component", y = "Proportion of Variance Explained") +
  theme_minimal()
sum(combined_lecontei_percent_var[1:15]) # 85.59% explained in first 15 PCs
lec_pca_scores<-combined_lecontei_pca$x
lec_centroid_size<-combined_lecontei_gpa$Csize 
combined_lecontei_pca_scores<-cbind.data.frame(ID,lec_centroid_size,lec_pca_scores)
combined_lecontei <- merge(x= combined_lecontei, y=combined_lecontei_pca_scores[,1:17], by = "ID") #Retaining Centroid + Comp1-15

combined_g0_lec <- combined_lecontei %>% subset(combined_lecontei$Treatment == "W")
combined_g0_lec$Treatment <- factor(combined_g0_lec$Treatment)
combined_g0_lec$Host <- factor(combined_g0_lec$Host)

combined_splits_lec <- combined_lecontei %>% subset(combined_lecontei$Treatment != "W")
combined_splits_lec$Treatment <- factor(combined_splits_lec$Treatment)
combined_splits_lec$Host <- factor(combined_splits_lec$Host)

# Computing combined_pinetum shape gpa
ID <- combined_pinetum[,1]
combined_pinetum_array <- arrayspecs(combined_pinetum[,18:81], 32, 2) 
mode(combined_pinetum_array) <- "numeric"
combined_pinetum_gpa <- gpagen(combined_pinetum_array, ProcD=F)
combined_pinetum_pca<-gm.prcomp(combined_pinetum_gpa$coords)
combined_pinetum_eig <- combined_pinetum_pca$d
combined_pinetum_percent_var <- (combined_pinetum_eig  / sum(combined_pinetum_eig )) * 100
temp_df <- data.frame(PC = 1:length(combined_pinetum_percent_var), Variance = combined_pinetum_percent_var)
ggplot(temp_df, aes(x = PC, y = Variance)) +
  geom_point() +
  geom_line() +
  scale_x_continuous(breaks = seq(0, 60, by=5)) +
  labs(title = "combined_pinetum Scree Plot", x = "Principal Component", y = "Proportion of Variance Explained") +
  theme_minimal()
sum(combined_pinetum_percent_var[1:15]) # 86.25% explained in first 15 PCs
pin_pca_scores<-combined_pinetum_pca$x
pin_centroid_size<-combined_pinetum_gpa$Csize 
combined_pinetum_pca_scores<-cbind.data.frame(ID,pin_centroid_size,pin_pca_scores)
combined_pinetum <- merge(x= combined_pinetum, y=combined_pinetum_pca_scores[,1:17], by = "ID") #Retaining Centroid + Comp1-15

combined_g0_pin <- combined_pinetum %>% subset(combined_pinetum$Treatment == "W")
combined_g0_pin$Treatment <- factor(combined_g0_pin$Treatment)
combined_g0_pin$Host <- factor(combined_g0_pin$Host)

combined_splits_pin <- combined_pinetum %>% subset(combined_pinetum$Treatment != "W")
combined_splits_pin$Treatment <- factor(combined_splits_pin$Treatment)
combined_splits_pin$Host <- factor(combined_splits_pin$Host)

# Subsetting GWAS samples
g0_lec_gwas <- combined_g0_lec %>% subset(combined_g0_lec$DNA == "Y")
seq_meta <- read.csv("fulldata_LecPine.csv", header = T)
g0_lec_gwas <- g0_lec_gwas %>%
  left_join(seq_meta %>% select(ind, ID, latitude, longitude, area, state), by = "ID")
g0_lec_gwas <- filter(g0_lec_gwas, ID != "AG007_F1" & ID != "AG078_F7")
#write.csv(g0_lec_gwas, file="g0_lec_gwas_v3.csv", row.names = F, quote=F)

library(car)
library(lmerTest)
library(emmeans)
library(performance)
library(see)
library(MetBrewer)

################################## G0 ########################################## 

# Setting contracts for Wald Type III ANOVAs
options(contrasts = c("contr.sum", "contr.poly"))

# Modeling combined_g0_all
model1_all <- lmer(Comp1~Species+(1|Colony), data = combined_g0_all)
Anova(model1_all, type = 2) # Species < 2.2e-16 ***

model2_all <- lmer(Comp2~Species+(1|Colony), data = combined_g0_all)
Anova(model2_all, type = 2) # Species 2.808e-08 ***

model3_all <- lmer(all_centroid_size~Species+(1|Colony), data = combined_g0_all)
Anova(model3_all, type = 2) # Species < 2.2e-16 ***

# Plotting combined_g0_all
ggplot(data = combined_g0_all, aes(Comp1, Comp2, fill = Host)) +
  geom_point(color = "black",size = 5, shape = 21) +
  scale_color_manual(values = met.brewer("Benedictus", n=14)) +
  scale_fill_manual(values = met.brewer("Benedictus", n=14)) +
  guides(fill = guide_legend(override.aes = list(shape = 21))) +
  theme_classic()

ggplot(data = combined_g0_all, aes(Comp1, all_centroid_size, fill = Host)) +
  geom_point(color = "black",size = 5, shape = 21) +
  scale_color_manual(values = met.brewer("Benedictus", n=14)) +
  scale_fill_manual(values = met.brewer("Benedictus", n=14)) +
  guides(fill = guide_legend(override.aes = list(shape = 21))) +
  theme_classic()

# Modeling combined_g0_lec shape
#model1_g0_lec <- lmer(Comp1~Host+(1|Colony), data = combined_g0_lec)
#Anova(model1_g0_lec, type = 2) # Host N.S.

#model2_g0_lec <- lmer(Comp2~Host+(1|Colony), data = combined_g0_lec)
#Anova(model2_g0_lec, type = 2) # Host 0.026 *
#emmeans(model2_g0_lec, pairwise~Host, adjust = "fdr") # red *

#model3_g0_lec <- lmer(Comp3~Host+(1|Colony), data = combined_g0_lec)
#Anova(model3_g0_lec, type = 2) # Host N.S.

model4_g0_lec <- lmer(Comp4~Host+(1|Colony), data = combined_g0_lec)
Anova(model4_g0_lec, type = 2) # Host 2.785e-14 ***
emmeans(model4_g0_lec, pairwise ~ Host, adjust = "fdr") # jack ***, red ***, pitch * 

model5_g0_lec <- lmer(Comp5~Host+(1|Colony), data = combined_g0_lec)
Anova(model5_g0_lec, type = 2) # Host 2.79e-07 ***
emmeans(model5_g0_lec, pairwise ~ Host, adjust = "fdr") # jack ***, red **

#model6_g0_lec <- lmer(Comp6~Host+(1|Colony), data = combined_g0_lec)
#Anova(model6_g0_lec, type = 2) # Host 0.002122 **
#emmeans(model6_g0_lec, pairwise ~ Host, adjust = "fdr") # N.S.

model7_g0_lec <- lmer(Comp7~Host+(1|Colony), data = combined_g0_lec)
Anova(model7_g0_lec, type = 2) # Host 0.003034 **
emmeans(model7_g0_lec, pairwise ~ Host, adjust = "fdr") # pitch *

#model8_g0_lec <- lmer(Comp8~Host+(1|Colony), data = combined_g0_lec)
#Anova(model8_g0_lec, type = 2) # Host 0.009412 **
#emmeans(model8_g0_lec, pairwise ~ Host, adjust = "fdr") # N.S.

model9_g0_lec <- lmer(Comp9~Host+(1|Colony), data = combined_g0_lec)
Anova(model9_g0_lec, type = 2) # Host 3.055e-06 ***
emmeans(model9_g0_lec, pairwise ~ Host, adjust = "fdr") # jack ***, slash *

#model10_g0_lec <- lmer(Comp10~Host+(1|Colony), data = combined_g0_lec)
#Anova(model10_g0_lec, type = 2) # Host 0.02994 *
#emmeans(model10_g0_lec, pairwise ~ Host, adjust = "fdr") # N.S.

model11_g0_lec <- lmer(Comp11~Host+(1|Colony), data = combined_g0_lec)
Anova(model11_g0_lec, type = 2) # Host 0.005371 **
emmeans(model11_g0_lec, pairwise ~ Host, adjust = "fdr") # jack **

#model12_g0_lec <- lmer(Comp12~Host+(1|Colony), data = combined_g0_lec)
#Anova(model12_g0_lec, type = 2) # Host 0.007875 **
#emmeans(model12_g0_lec, pairwise ~ Host, adjust = "fdr") # N.S.

#model13_g0_lec <- lmer(Comp13~Host+(1|Colony), data = combined_g0_lec)
#Anova(model13_g0_lec, type = 2) # Host 0.001157 **
#emmeans(model11_g0_lec, pairwise ~ Host, adjust = "fdr") # jack *

model14_g0_lec <- lmer(Comp14~Host+(1|Colony), data = combined_g0_lec)
Anova(model14_g0_lec, type = 2) # Host 0.000306 ***
emmeans(model14_g0_lec, pairwise ~ Host, adjust = "fdr") # red*, austrian *, virginia *

#model15_g0_lec <- lmer(Comp15~Host+(1|Colony), data = combined_g0_lec)
#Anova(model15_g0_lec, type = 2) # Host 0.381

model16_g0_lec <- lmer(lec_centroid_size~body_length*Host+(1|Colony), data = combined_g0_lec)
Anova(model16_g0_lec, type = 3) # body_length 0.0029603 **; Host 0.0017410 **; body_length:Host 0.0002137 ***
emmeans(model16_g0_lec, pairwise ~ Host, adjust = "fdr") # red **, longleaf **, slash *

model17_g0_lec <- lmer(Tooth1LM~body_length+Host+(1|Colony), data = combined_g0_lec)
Anova(model17_g0_lec, type = 2) # Host 1.895e-06 ***
emmeans(model17_g0_lec, pairwise ~ Host, adjust = "fdr") # red ***, longleaf **

model18_g0_lec <- lmer(Ann2LM~body_length*Host+(1|Colony), data = combined_g0_lec)
Anova(model18_g0_lec, type = 3) # body_length 0.0203712 *; Host 0.0002632 ***; body_length:Host 1.466e-05 ***
emmeans(model18_g0_lec, pairwise ~ Host, adjust = "fdr") # jack ***, longleaf ***, slash **

#model19_g0_lec <- lmer(Ann8LM~body_length+Host+(1|Colony), data = combined_g0_lec)
#Anova(model19_g0_lec, type = 2) # Host 0.01471 *
#emmeans(model19_g0_lec, pairwise ~ Host, adjust = "fdr") # N.S.

model20_g0_lec <- lmer(BottomLengthLM~body_length*Host+(1|Colony), data = combined_g0_lec)
Anova(model20_g0_lec, type = 3) # body_length 0.001888 **; Host 0.008039 **; body_length:Host 0.001906 **
emmeans(model20_g0_lec, pairwise ~ Host, adjust = "fdr") # red **, longleaf **

model21_g0_lec <- lmer(body_length~Host+(1|Colony), data = combined_g0_lec)
Anova(model21_g0_lec, type = 2) # Host 0.008075 **

# Plotting combined_lecontei
ggplot(data = combined_g0_lec, aes(Comp4, Comp5, fill = Host, shape = Treatment)) +
  geom_point(color = "black",size = 5) +
  scale_shape_manual(values = c(21, 22, 23)) +
  scale_color_manual(values = met.brewer("Benedictus", n=14)) +
  scale_fill_manual(values = met.brewer("Benedictus", n=14)) +
  guides(fill = guide_legend(override.aes = list(shape = 21))) +
  theme_classic()

# Modeling combined_g0_pin shape
model1_g0_pin <- lmer(Comp1~Latitude+(1|Colony), data = combined_g0_pin)
Anova(model1_g0_pin, type = 2) # Latitude 0.0316 *

#model2_g0_pin <- lmer(Comp2~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model2_g0_pin, type = 2) # N.S.
#model3_g0_pin <- lmer(Comp3~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model3_g0_pin, type = 2) # N.S.
#model4_g0_pin <- lmer(Comp4~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model4_g0_pin, type = 2) # N.S.
#model5_g0_pin <- lmer(Comp5~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model5_g0_pin, type = 2) # N.S.
#model6_g0_pin <- lmer(Comp6~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model6_g0_pin, type = 2) # N.S.

model7_g0_pin <- lmer(Comp7~Latitude+(1|Colony), data = combined_g0_pin)
Anova(model7_g0_pin, type = 2) # Latitude 0.0114 *

#model8_g0_pin <- lmer(Comp8~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model8_g0_pin, type = 2) # N.S.
#model9_g0_pin <- lmer(Comp9~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model9_g0_pin, type = 2) # N.S.
#model10_g0_pin <- lmer(Comp10~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model10_g0_pin, type = 2) # N.S.
#model11_g0_pin <- lmer(pin_centroid_size~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model11_g0_pin, type = 2) # N.S.

model12_g0_pin <- lmer(Tooth1LM~Latitude+(1|Colony), data = combined_g0_pin)
Anova(model12_g0_pin, type = 2) # Latitide 8.966e-05 ***

#model13_g0_pin <- lmer(Ann2LM~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model13_g0_pin, type = 2) # N.S.
#model14_g0_pin <- lmer(BottomLengthLM~Latitude+(1|Colony), data = combined_g0_pin)
#Anova(model14_g0_pin, type = 2) # N.S.

############################### Splits #########################################

# Modeling combined_splits_lec
model1_splits_lec <- lm(Comp4 ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model1_splits_lec,type=3) # Colony 4.827e-05 ***

model1.2_splits_lec <- lm(Comp4 ~ Colony+Host, data = combined_splits_lec)
Anova(model1.2_splits_lec,type=2) # Colony 2.856e-05 ***

model2_splits_lec <- lm(Comp5 ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model2_splits_lec,type=3) # Colony 2.983e-08 ***

model2.2_splits_lec <- lm(Comp5 ~ Colony+Host, data = combined_splits_lec)
Anova(model2.2_splits_lec,type=3) # Colony 1.689e-08 ***

model3_splits_lec <- lm(Comp9 ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model3_splits_lec,type=3) # Colony 0.001989 **

model3.2_splits_lec <- lm(Comp9 ~ Colony+Host, data = combined_splits_lec)
Anova(model3.2_splits_lec,type=2) # Colony 0.001278 **

model4_splits_lec <- lm(Comp11 ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model4_splits_lec,type=3) # Colony 6.207e-08 ***

model4.2_splits_lec <- lm(Comp11 ~ Colony+Host, data = combined_splits_lec)
Anova(model4.2_splits_lec,type=2) # Colony 5.467e-08 ***

model5_splits_lec <- lm(Comp14 ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model5_splits_lec,type=3) # Colony 6.897e-05 ***

model5.2_splits_lec <- lm(Comp14 ~ Colony+Host, data = combined_splits_lec)
Anova(model5.2_splits_lec,type=2) # Colony 6.689e-05 ***

model6_splits_lec <- lm(lec_centroid_size ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model6_splits_lec,type=3) # Colony 0.0002581 ***; Host 1.592e-08 ***; Colony:Host 0.0302198 *

model7_splits_lec <- lm(Tooth1LM ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model7_splits_lec,type=3) # Colony 1.566e-09 ***

model7.2_splits_lec <- lm(Tooth1LM ~ Colony+Host, data = combined_splits_lec)
Anova(model7.2_splits_lec,type=2) # Colony 1.183e-09 ***

model8_splits_lec <- lm(Ann2LM ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model8_splits_lec,type=3) # Host 3.881e-06 ***

model8.2_splits_lec <- lm(Ann2LM ~ Colony+Host, data = combined_splits_lec)
Anova(model8.2_splits_lec,type=2) # Host 2.442e-07 ***

model9_splits_lec <- lm(BottomLengthLM ~ Colony+Host+Host*Colony, data = combined_splits_lec)
Anova(model9_splits_lec,type=3) # Colony 9.608e-05 ***; Host 4.457e-09 ***; Colony:Host 0.025768 *

# Modeling combined_splits_pin
model1_splits_pin <- lm(Comp1 ~ Colony+Host+Host*Colony, data = combined_splits_pin)
Anova(model1_splits_pin,type=3) # Colony 0.0001013 ***; Host 0.0004289 ***; Colony:Host 0.0092895 **

model2_splits_pin <- lm(Comp7 ~ Colony+Host+Host*Colony, data = combined_splits_pin)
Anova(model2_splits_pin,type=3) # Colony 1.789e-10 ***; Host 0.02377 *

model3_splits_pin <- lm(pin_centroid_size ~ Colony+Host+Host*Colony, data = combined_splits_pin)
Anova(model3_splits_pin,type=3) # Colony 1.045e-12 ***; Host < 2.2e-16 ***; Colony:Host 0.001174 ** 

#model4_splits_pin <- lm(Tooth1LM ~ Colony+Host+Host*Colony, data = combined_splits_pin)
#Anova(model4_splits_pin,type=3) # N.S.

model4.2_splits_pin <- lm(Tooth1LM ~ Colony+Host, data = combined_splits_pin)
Anova(model4.2_splits_pin,type=2) # Host 0.01701 *

model5_splits_pin <- lm(Ann2LM ~ Colony+Host+Host*Colony, data = combined_splits_pin)
Anova(model5_splits_pin,type=3) # Colony 7.380e-06 ***; Host 8.732e-14 ***; Colony:Host 0.007548 ** 

model5_splits_pin <- lm(BottomLengthLM ~ Colony +Host+Host*Colony, data = combined_splits_pin)
Anova(model5_splits_pin,type=3) # Colony  1.036e-14 ***; Host 1.154e-11 ***; Colony:Host 0.008895 ** 
