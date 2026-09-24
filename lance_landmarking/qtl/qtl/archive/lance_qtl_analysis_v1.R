setwd("~/Academia/Ovipositor_QTL/LancePartyUSA/phenotype_genotype/qtl")

library(readxl)
library(dplyr)
library(ggplot2)

lance_right_pheno <- read.csv(file="PRIME_LanceRight_Pheno_v3.csv",header=TRUE)
lance_left_pheno <- read.csv(file="PRIME_LanceLeft_Pheno_v3.csv",header=TRUE)
lance_bottom_pheno <- read.csv(file="PRIME_LanceBottom_Pheno_v3.csv",header=TRUE)

## LBX Preparation ##
LBX_saw_pheno_geno <- read.csv(file="LBX_25kb_saw_qtl-tocombine.csv",header=TRUE)

LBX_lance_right_pheno_geno <- left_join(LBX_saw_pheno_geno, lance_right_pheno, by = join_by(ID))
#write.csv(LBX_lance_right_pheno_geno,file="LBX_LanceRight_QTL.csv",quote=FALSE)
LBX_lance_left_pheno_geno <- left_join(LBX_saw_pheno_geno, lance_left_pheno, by = join_by(ID))
#write.csv(LBX_lance_left_pheno_geno,file="LBX_LanceLeft_QTL.csv",quote=FALSE)
LBX_lance_bottom_pheno_geno <- left_join(LBX_saw_pheno_geno, lance_bottom_pheno, by = join_by(ID))
#write.csv(LBX_lance_bottom_pheno_geno,file="LBX_LanceBottom_QTL.csv",quote=FALSE)

## PBX Preparation ##
PBX_saw_pheno_geno <- read.csv(file="PBX_25kb_2024_qtl_tocombine.csv",header=TRUE)

PBX_lance_right_pheno_geno <- left_join(PBX_saw_pheno_geno, lance_right_pheno, by = join_by(ID))
#write.csv(PBX_lance_right_pheno_geno,file="PBX_LanceRight_QTL.csv",quote=FALSE)
PBX_lance_left_pheno_geno <- left_join(PBX_saw_pheno_geno, lance_left_pheno, by = join_by(ID))
#write.csv(PBX_lance_left_pheno_geno,file="PBX_LanceLeft_QTL.csv",quote=FALSE)
PBX_lance_bottom_pheno_geno <- left_join(PBX_saw_pheno_geno, lance_bottom_pheno, by = join_by(ID))
#write.csv(PBX_lance_bottom_pheno_geno,file="PBX_LanceBottom_QTL.csv",quote=FALSE)


library(qtl)
## Saw Data ##
LBX_Saw<-read.cross(format="csv",file="LBX_LanceRight_QTL_v2.csv",crosstype ="bc",na.strings="NA",genotypes=c("AA","AB"), estimate.map=FALSE)
LBX_Saw<-jittermap(LBX_Saw)

LBX_Saw <- calc.genoprob(LBX_Saw, step=0, error.prob = 0.01, map.function = "kosambi",stepwidth = "fixed")
LBX_Saw_Fam <- as.numeric(pull.pheno(LBX_Saw, pheno.col="Family"))

#families with one individual are not meaningful covariates; reduce to only those with >1
#first count number in each site
#test<-as.data.frame(cbind(LBX_Saw$pheno$ID,LBX_Saw_Fam))
#test%>%count(as.factor(LBX_Saw_Fam))
#exclude families 12, 16,17as covariates

LBX_Saw_Fam1 <-as.numeric(LBX_Saw_Fam == 1)
LBX_Saw_Fam2 <- as.numeric (LBX_Saw_Fam == 2)
LBX_Saw_Fam3 <- as.numeric (LBX_Saw_Fam == 3)
LBX_Saw_Fam4 <- as.numeric (LBX_Saw_Fam == 4)
LBX_Saw_Fam5 <- as.numeric (LBX_Saw_Fam == 5)
LBX_Saw_Fam6 <- as.numeric (LBX_Saw_Fam == 6)
LBX_Saw_Fam7 <- as.numeric (LBX_Saw_Fam == 7)
LBX_Saw_Fam8 <- as.numeric (LBX_Saw_Fam == 8)
LBX_Saw_Fam9 <- as.numeric (LBX_Saw_Fam == 9)
LBX_Saw_Fam10 <- as.numeric (LBX_Saw_Fam == 10)
LBX_Saw_Fam11 <- as.numeric (LBX_Saw_Fam == 11)
#LBX_Saw_Fam12 <- as.numeric (LBX_Saw_Fam == 12)
LBX_Saw_Fam13 <- as.numeric (LBX_Saw_Fam == 13)
LBX_Saw_Fam14 <- as.numeric (LBX_Saw_Fam == 14)
LBX_Saw_Fam15 <- as.numeric (LBX_Saw_Fam == 15)
#LBX_Saw_Fam16 <- as.numeric (LBX_Saw_Fam == 16)
#LBX_Saw_Fam17 <- as.numeric (LBX_Saw_Fam == 17)
LBX_Saw_Fam18 <- as.numeric (LBX_Saw_Fam == 18)
LBX_Saw_Fam19 <- as.numeric (LBX_Saw_Fam == 19)

LBX_Saw_Fam_X <- cbind(LBX_Saw_Fam1,LBX_Saw_Fam2,LBX_Saw_Fam3,LBX_Saw_Fam4,LBX_Saw_Fam5,LBX_Saw_Fam6,LBX_Saw_Fam7,LBX_Saw_Fam8,LBX_Saw_Fam9,LBX_Saw_Fam10,LBX_Saw_Fam11,LBX_Saw_Fam13,LBX_Saw_Fam14,LBX_Saw_Fam15,LBX_Saw_Fam18,LBX_Saw_Fam19)
LBX_Saw_Host <- as.numeric(pull.pheno(LBX_Saw, pheno.col="WhiteChoice"))
LBX_Saw_BodySize <- as.numeric(pull.pheno(LBX_Saw, pheno.col="leg_length"))

LBX_Saw_CoVar_Host <- cbind(LBX_Saw_Host, LBX_Saw_Fam_X)
LBX_Saw_CoVar_Body <-cbind(LBX_Saw_BodySize, LBX_Saw_Fam_X)
LBX_Saw_CoVar_All <-cbind (LBX_Saw_Host, LBX_Saw_BodySize, LBX_Saw_Fam_X)

# Bottom Length
BottomLengthLM<-scanone(LBX_Saw, pheno.col="SawBottomLengthLM", method="hk", model="normal", addcovar=LBX_Saw_CoVar_Body)
plot(BottomLengthLM)

# Ann2LM
Ann2LM<-scanone(LBX_Saw, pheno.col="SawAnn2LM", method="hk", model="normal", addcovar=LBX_Saw_CoVar_Body)
plot(Ann2LM)

# Ann8LM
Ann8LM<-scanone(LBX_Saw, pheno.col="SawAnn8LM", method="hk", model="normal", addcovar=LBX_Saw_CoVar_Body)
plot(Ann8LM)

# Centroid
landmarks_centroid<-scanone(LBX_Saw, pheno.col="Sawlandmarks_centroid", method="hk", model="normal", addcovar=LBX_Saw_CoVar_Body)
plot(landmarks_centroid)

BottomLengthLM.df <- as.data.frame(BottomLengthLM)
Ann2LM.df <- as.data.frame(Ann2LM)
Ann8LM.df <- as.data.frame(Ann8LM)
landmarks_centroid.df <- as.data.frame(landmarks_centroid)


## LBX Analysis ##
LBX_Right <- read.cross(format="csv",file="LBX_LanceRight_QTL_v2.csv",crosstype ="bc",na.strings="NA",genotypes=c("AA","AB"), estimate.map=FALSE)
LBX_Right <- jittermap(LBX_Right)
LBX_Left <- read.cross(format="csv",file="LBX_LanceLeft_QTL_v2.csv",crosstype ="bc",na.strings="NA",genotypes=c("AA","AB"), estimate.map=FALSE)
LBX_Left <- jittermap(LBX_Left)
LBX_Bottom <- read.cross(format="csv",file="LBX_LanceBottom_QTL_v2.csv",crosstype ="bc",na.strings="NA",genotypes=c("AA","AB"), estimate.map=FALSE)
LBX_Bottom <- jittermap(LBX_Bottom)

# LBX Right
LBX_Right <- calc.genoprob(LBX_Right, step=0, error.prob = 0.01, map.function = "kosambi",stepwidth = "fixed")
LBX_Right_Fam <- as.numeric(pull.pheno(LBX_Right, pheno.col="Family"))

#families with one individual are not meaningful covariates; reduce to only those with >1
#first count number in each site
#test<-as.data.frame(cbind(LBX_Right$pheno$ID,LBX_Right_Fam))
#test%>%count(as.factor(LBX_Right_Fam))
#exclude families 12, 16,17as covariates

LBX_Right_Fam1 <-as.numeric(LBX_Right_Fam == 1)
LBX_Right_Fam2 <- as.numeric (LBX_Right_Fam == 2)
LBX_Right_Fam3 <- as.numeric (LBX_Right_Fam == 3)
LBX_Right_Fam4 <- as.numeric (LBX_Right_Fam == 4)
LBX_Right_Fam5 <- as.numeric (LBX_Right_Fam == 5)
LBX_Right_Fam6 <- as.numeric (LBX_Right_Fam == 6)
LBX_Right_Fam7 <- as.numeric (LBX_Right_Fam == 7)
LBX_Right_Fam8 <- as.numeric (LBX_Right_Fam == 8)
LBX_Right_Fam9 <- as.numeric (LBX_Right_Fam == 9)
LBX_Right_Fam10 <- as.numeric (LBX_Right_Fam == 10)
LBX_Right_Fam11 <- as.numeric (LBX_Right_Fam == 11)
#LBX_Right_Fam12 <- as.numeric (LBX_Right_Fam == 12)
LBX_Right_Fam13 <- as.numeric (LBX_Right_Fam == 13)
LBX_Right_Fam14 <- as.numeric (LBX_Right_Fam == 14)
LBX_Right_Fam15 <- as.numeric (LBX_Right_Fam == 15)
#LBX_Right_Fam16 <- as.numeric (LBX_Right_Fam == 16)
#LBX_Right_Fam17 <- as.numeric (LBX_Right_Fam == 17)
LBX_Right_Fam18 <- as.numeric (LBX_Right_Fam == 18)
LBX_Right_Fam19 <- as.numeric (LBX_Right_Fam == 19)

LBX_Right_Fam_X <- cbind(LBX_Right_Fam1,LBX_Right_Fam2,LBX_Right_Fam3,LBX_Right_Fam4,LBX_Right_Fam5,LBX_Right_Fam6,LBX_Right_Fam7,LBX_Right_Fam8,LBX_Right_Fam9,LBX_Right_Fam10,LBX_Right_Fam11,LBX_Right_Fam13,LBX_Right_Fam14,LBX_Right_Fam15,LBX_Right_Fam18,LBX_Right_Fam19)
LBX_Right_Host <- as.numeric(pull.pheno(LBX_Right, pheno.col="WhiteChoice"))
LBX_Right_BodySize <- as.numeric(pull.pheno(LBX_Right, pheno.col="leg_length"))

LBX_Right_CoVar_Host <- cbind(LBX_Right_Host, LBX_Right_Fam_X)
LBX_Right_CoVar_Body <-cbind(LBX_Right_BodySize, LBX_Right_Fam_X)
LBX_Right_CoVar_All <-cbind (LBX_Right_Host, LBX_Right_BodySize, LBX_Right_Fam_X)

#Shape PCA Comp #1
LBX_Comp1_Right <- scanone(LBX_Right, pheno.col="Comp1", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp1_Right)
LBX_Comp1_Right.scanone.perm <- scanone(LBX_Right,method="hk",pheno.col="Comp1", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_Comp1_Right,perms=LBX_Comp1_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr3 & 4 - 2 peaks - >0.001 to 0.014

# Shape PCA Comp #2
LBX_Comp2_Right <- scanone(LBX_Right, pheno.col="Comp2", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp2_Right)

# Shape PCA Comp #3
LBX_Comp3_Right <- scanone(LBX_Right, pheno.col="Comp3", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp3_Right)

# Shape PCA Comp #4
LBX_Comp4_Right <- scanone(LBX_Right, pheno.col="Comp4", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp4_Right)

# Shape PCA Comp #5
LBX_Comp5_Right <- scanone(LBX_Right, pheno.col="Comp5", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp5_Right)

# Shape PCA Comp #6
LBX_Comp6_Right <- scanone(LBX_Right, pheno.col="Comp6", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp6_Right)

# Shape PCA Comp #7
LBX_Comp7_Right <- scanone(LBX_Right, pheno.col="Comp7", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp7_Right)

# Shape PCA Comp #8
LBX_Comp8_Right <- scanone(LBX_Right, pheno.col="Comp8", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp8_Right)

# Shape PCA Comp #9
LBX_Comp9_Right <- scanone(LBX_Right, pheno.col="Comp9", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp9_Right)

# Shape PCA Comp #10
LBX_Comp10_Right <- scanone(LBX_Right, pheno.col="Comp10", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp10_Right)

# Shape PCA Comp #11
LBX_Comp11_Right <- scanone(LBX_Right, pheno.col="Comp11", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp11_Right)

# Shape PCA Comp #12
LBX_Comp12_Right <- scanone(LBX_Right, pheno.col="Comp12", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Comp12_Right)
LBX_Comp12_Right.scanone.perm <- scanone(LBX_Right,method="hk",pheno.col="Comp12", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_Comp12_Right,perms=LBX_Comp12_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr4 - 1 peaks -  0.025

LBX_Comp1_Right.df <- as.data.frame(LBX_Comp1_Right)
LBX_Comp5_Right.df <- as.data.frame(LBX_Comp5_Right)
LBX_Comp12_Right.df <- as.data.frame(LBX_Comp12_Right)

shape_to_length_right <- ggplot(NULL, aes(pos, lod)) + 
  geom_line(data = LBX_Comp1_Right.df, color = "coral1", linewidth = 1) + 
  geom_line(data = LBX_Comp12_Right.df, color = "steelblue1", linewidth = 1) +
  geom_line(data = BottomLengthLM.df, color = "azure3", linewidth = 1) +
  geom_line(data = landmarks_centroid.df, color = "azure4", linewidth = 1) +
  facet_grid(.~ chr, scales = "free_x") +
  theme_classic()
print(shape_to_length_right)

shape_to_width_right <- ggplot(NULL, aes(pos, lod)) + 
  geom_line(data = LBX_Comp1_Right.df, color = "coral1", linewidth = 1) + 
  geom_line(data = LBX_Comp12_Right.df, color = "steelblue1", linewidth = 1) +
  geom_line(data = Ann2LM.df, color = "azure3", linewidth = 1) +
  geom_line(data = Ann8LM.df, color = "azure4", linewidth = 1) +
  facet_grid(.~ chr, scales = "free_x") +
  theme_classic()
print(shape_to_width_right)

# Centroid Size
LBX_Centroid_Size_Right <- scanone(LBX_Right, pheno.col="centroid_size_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_centroid_size_right)

# Cuticular Window Length
LBX_Cutwindow_Length_Right <- scanone(LBX_Right, pheno.col="Cutwindow_length_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Cutwindow_Length_Right)

# Distance from Cuticular window to Tip #1
LBX_Window_to_Edge1_Right <- scanone(LBX_Right, pheno.col="window_to_edge1", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Window_to_Edge1_Right)
LBX_Window_to_Edge1_Right.scanone.perm<-scanone(LBX_Right,method="hk",pheno.col="window_to_edge1", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_Window_to_Edge1_Right,perms=LBX_Window_to_Edge1_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr4 - 1 peak - 0.03

LBX_Window_to_Edge1_Right.df <- as.data.frame(LBX_Window_to_Edge1_Right)

cutwindow_to_length_right <- ggplot(NULL, aes(pos, lod)) + 
  geom_line(data = LBX_Window_to_Edge1_Right.df, color = "coral1", linewidth = 1) + 
  geom_line(data = BottomLengthLM.df, color = "azure3", linewidth = 1) +
  geom_line(data = landmarks_centroid.df, color = "azure4", linewidth = 1) +
  facet_grid(.~ chr, scales = "free_x") +
  theme_classic()
print(cutwindow_to_length_right)

# Suture #1 Length
LBX_Sut1_Length_Right <- scanone(LBX_Right, pheno.col="Sut1_length_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Sut1_Length_Right)

# Suture #2 Length
LBX_Sut2_Length_Right <- scanone(LBX_Right, pheno.col="Sut2_length_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Sut2_Length_Right)

# Suture #3 Length
LBX_Sut3_Length_Right <- scanone(LBX_Right, pheno.col="Sut3_length_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Sut3_Length_Right)

# Suture #4 Length
LBX_Sut4_Length_Right <- scanone(LBX_Right, pheno.col="Sut4_length_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Sut4_Length_Right)

# Suture #5 Length
LBX_Sut5_Length_Right <- scanone(LBX_Right, pheno.col="Sut5_length_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Sut5_Length_Right)

# Suture #6 Length
LBX_Sut6_Length_Right <- scanone(LBX_Right, pheno.col="Sut6_length_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Sut6_Length_Right)
LBX_Sut6_Length_Right.scanone.perm<-scanone(LBX_Right,method="hk",pheno.col="Sut6_length_right", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_Sut6_Length_Right,perms=LBX_Sut6_Length_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr6 - 1 peak - 0.04

# Arch #1 Width
LBX_Arc1_Width_Right <- scanone(LBX_Right, pheno.col="Arc1_width_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Arc1_Width_Right)

# Arch #2 Width
LBX_Arc2_Width_Right <- scanone(LBX_Right, pheno.col="Arc2_width_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Arc2_Width_Right)

# Arch #3 Width
LBX_Arc3_Width_Right <- scanone(LBX_Right, pheno.col="Arc3_width_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Arc3_Width_Right)

# Arch #4 Width
LBX_Arc4_Width_Right <- scanone(LBX_Right, pheno.col="Arc4_width_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Arc4_Width_Right)

# Arch #5 Width
LBX_Arc5_Width_Right <- scanone(LBX_Right, pheno.col="Arc5_width_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Arc5_Width_Right)
LBX_Arc5_Width_Right.scanone.perm<-scanone(LBX_Right,method="hk",pheno.col="Arc5_width_right", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_Arc5_Width_Right,perms=LBX_Arc5_Width_Right.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr6 - 1 peak - 0.011

# Arch #6 Width
LBX_Arc6_Width_Right <- scanone(LBX_Right, pheno.col="Arc6_width_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Arc6_Width_Right)

# Total Length
LBX_Rightface_Length <- scanone(LBX_Right, pheno.col="Rightface_len", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Rightface_Length)

# Length of the Cutting Edge
LBX_Cut_Edge_Length <- scanone(LBX_Right, pheno.col="cut_edge_length", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Cut_Edge_Length)

# Rail Height
LBX_Rail_Height_Right <- scanone(LBX_Right, pheno.col="Intersect_to_top_dist_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Rail_Height_Right)
LBX_Rail_Height_Right.scanone.perm<-scanone(LBX_Right,method="hk",pheno.col="Intersect_to_top_dist_right", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_Rail_Height_Right,perms=LBX_Rail_Height_Right.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr5 - 1 peak - 0.03

# Distance from Arch 2 to 3
LBX_Dist_Arc2_Arc3_Right <- scanone(LBX_Right, pheno.col="dist_arc2_arc3_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Dist_Arc2_Arc3_Right)

# Distance from Arch 3 to 4
LBX_Dist_Arc3_Arc4_Right <- scanone(LBX_Right, pheno.col="dist_arc3_arc4_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Dist_Arc3_Arc4_Right)

# Distance from Arch 4 to 5
LBX_Dist_Arc4_Arc5_Right <- scanone(LBX_Right, pheno.col="dist_arc4_arc5_right", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Dist_Arc4_Arc5_Right)

# Right Face Height #1
LBX_RightFace_Height1 <- scanone(LBX_Right, pheno.col="Rightface_height1", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_RightFace_Height1)
LBX_RightFace_Height1.scanone.perm<-scanone(LBX_Right,method="hk",pheno.col="Rightface_height1", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_RightFace_Height1,perms=LBX_RightFace_Height1.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr2 - 1 peak - 0.013

# Right Face Height #2
LBX_RightFace_Height2 <- scanone(LBX_Right, pheno.col="Rightface_height2", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_RightFace_Height2)
RightFace_Height2.scanone.perm<-scanone(LBX_Right,method="hk",pheno.col="Rightface_height2", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_RightFace_Height2,perms=LBX_RightFace_Height2.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr2 - 1 peak - 0.006

# Right Face Height #3
LBX_RightFace_Height3 <- scanone(LBX_Right, pheno.col="Rightface_height3", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_RightFace_Height3)

# Right Face Height #4
LBX_RightFace_Height4 <- scanone(LBX_Right, pheno.col="Rightface_height4", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_RightFace_Height4)

# Right Face Height #5
LBX_RightFace_Height5 <- scanone(LBX_Right, pheno.col="Rightface_height5", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_RightFace_Height5)

# Right Face Height #6
LBX_RightFace_Height6 <- scanone(LBX_Right, pheno.col="Rightface_height6", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_RightFace_Height6)

# Right Face Height #7
LBX_RightFace_Height7 <- scanone(LBX_Right, pheno.col="Rightface_height7", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(RightFace_Height7)
LBX_RightFace_Height7.scanone.perm<-scanone(LBX_Right,method="hk",pheno.col="Rightface_height7", addcovar=LBX_Right_CoVar_Body, n.perm=1000)
summary(LBX_RightFace_Height7,perms=LBX_RightFace_Height7.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peak - 0.01

# Depth of the Cutting Edge #1
LBX_Cutting_Depth1 <- scanone(LBX_Right, pheno.col="cutting_depth1", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Cutting_Depth1)

# Depth of the Cutting Edge #2
LBX_Cutting_Depth2 <- scanone(LBX_Right, pheno.col="cutting_depth2", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Cutting_Depth2)

# Right Face Rail Length
LBX_Rail_Length_Right <- scanone(LBX_Right, pheno.col="rail_length", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Rail_Length_Right)

# Distance from Bottom of the Cuticular Window to the Rail
LBX_Window_to_Rail_Right <- scanone(LBX_Right, pheno.col="window_to_rail", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Window_to_Rail_Right)

# Reveresed Asymetry of the Cutting Edge
LBX_Cut_Edge_Aysmmetry <- scanone(LBX_Right, pheno.col="cut_edge_aysmmetry", method="hk", model="normal", addcovar=LBX_Right_CoVar_Body)
plot(LBX_Cut_Edge_Aysmmetry)


## -------------------------------------------------------------------------- ##


# LBX Left
LBX_Left <- calc.genoprob(LBX_Left, step=0, error.prob = 0.01, map.function = "kosambi",stepwidth = "fixed")
LBX_Left_Fam <- as.numeric(pull.pheno(LBX_Left, pheno.col="Family"))

#families with one individual are not meaningful covariates; reduce to only those with >1
#first count number in each site
#test<-as.data.frame(cbind(LBX_Left$pheno$ID,LBX_Left_Fam))
#test%>%count(as.factor(LBX_Left_Fam))
#exclude families 12, 16,17 as covariates

LBX_Left_Fam1 <-as.numeric(LBX_Left_Fam == 1)
LBX_Left_Fam2 <- as.numeric (LBX_Left_Fam == 2)
LBX_Left_Fam3 <- as.numeric (LBX_Left_Fam == 3)
LBX_Left_Fam4 <- as.numeric (LBX_Left_Fam == 4)
LBX_Left_Fam5 <- as.numeric (LBX_Left_Fam == 5)
LBX_Left_Fam6 <- as.numeric (LBX_Left_Fam == 6)
LBX_Left_Fam7 <- as.numeric (LBX_Left_Fam == 7)
LBX_Left_Fam8 <- as.numeric (LBX_Left_Fam == 8)
LBX_Left_Fam9 <- as.numeric (LBX_Left_Fam == 9)
LBX_Left_Fam10 <- as.numeric (LBX_Left_Fam == 10)
LBX_Left_Fam11 <- as.numeric (LBX_Left_Fam == 11)
#LBX_Left_Fam12 <- as.numeric (LBX_Left_Fam == 12)
LBX_Left_Fam13 <- as.numeric (LBX_Left_Fam == 13)
LBX_Left_Fam14 <- as.numeric (LBX_Left_Fam == 14)
LBX_Left_Fam15 <- as.numeric (LBX_Left_Fam == 15)
#LBX_Left_Fam16 <- as.numeric (LBX_Left_Fam == 16)
#LBX_Left_Fam17 <- as.numeric (LBX_Left_Fam == 17)
LBX_Left_Fam18 <- as.numeric (LBX_Left_Fam == 18)
LBX_Left_Fam19 <- as.numeric (LBX_Left_Fam == 19)

LBX_Left_Fam_X <- cbind(LBX_Left_Fam1,LBX_Left_Fam2,LBX_Left_Fam3,LBX_Left_Fam4,LBX_Left_Fam5,LBX_Left_Fam6,LBX_Left_Fam7,LBX_Left_Fam8,LBX_Left_Fam9,LBX_Left_Fam10,LBX_Left_Fam11,LBX_Left_Fam13,LBX_Left_Fam14,LBX_Left_Fam15,LBX_Left_Fam18,LBX_Left_Fam19)
LBX_Left_Host <- as.numeric(pull.pheno(LBX_Left, pheno.col="WhiteChoice"))
LBX_Left_BodySize <- as.numeric(pull.pheno(LBX_Left, pheno.col="leg_length"))

LBX_Left_CoVar_Host <- cbind(LBX_Left_Host, LBX_Left_Fam_X)
LBX_Left_CoVar_Body <-cbind(LBX_Left_BodySize, LBX_Left_Fam_X)
LBX_Left_CoVar_All <-cbind (LBX_Left_Host, LBX_Left_BodySize, LBX_Left_Fam_X)

#Shape PCA Comp #1
LBX_Comp1_Left <- scanone(LBX_Left, pheno.col="Comp1", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp1_Left)
LBX_Comp1_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="Comp1", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Comp1_Left,perms=LBX_Comp1_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 & 5 - 2 peaks - 0.012 to 0.031

# Shape PCA Comp #2
LBX_Comp2_Left <- scanone(LBX_Left, pheno.col="Comp2", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp2_Left)

# Shape PCA Comp #3
LBX_Comp3_Left <- scanone(LBX_Left, pheno.col="Comp3", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp3_Left)
LBX_Comp3_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="Comp3", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Comp3_Left,perms=LBX_Comp3_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr3 - 1 peaks - 0.007

# Shape PCA Comp #4
LBX_Comp4_Left <- scanone(LBX_Left, pheno.col="Comp4", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp4_Left)

# Shape PCA Comp #5
LBX_Comp5_Left <- scanone(LBX_Left, pheno.col="Comp5", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp5_Left)

# Shape PCA Comp #6
LBX_Comp6_Left <- scanone(LBX_Left, pheno.col="Comp6", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp6_Left)
LBX_Comp6_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="Comp6", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Comp6_Left,perms=LBX_Comp6_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peaks - 0.004

# Shape PCA Comp #7
LBX_Comp7_Left <- scanone(LBX_Left, pheno.col="Comp7", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp7_Left)

# Shape PCA Comp #8
LBX_Comp8_Left <- scanone(LBX_Left, pheno.col="Comp8", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp8_Left)

# Shape PCA Comp #9
LBX_Comp9_Left <- scanone(LBX_Left, pheno.col="Comp9", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp9_Left)

# Shape PCA Comp #10
LBX_Comp10_Left <- scanone(LBX_Left, pheno.col="Comp10", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp10_Left) # !!!
LBX_Comp10_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="Comp10", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Comp10_Left,perms=LBX_Comp10_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peaks - 0.026

# Shape PCA Comp #11
LBX_Comp11_Left <- scanone(LBX_Left, pheno.col="Comp11", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp11_Left)

# Shape PCA Comp #12
LBX_Comp12_Left <- scanone(LBX_Left, pheno.col="Comp12", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Comp12_Left)

# Centroid Size
LBX_Centroid_Size_Left <- scanone(LBX_Left, pheno.col="centroid_size_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Centroid_Size_Left)
LBX_Centroid_Size_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="centroid_size_left", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Centroid_Size_Left,perms=LBX_Centroid_Size_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr2 - 1 peaks - 0.026

# Cuticular Window Length
LBX_Cutwindow_Length_Left <- scanone(LBX_Left, pheno.col="Cutwindow_length_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Cutwindow_Length_Left)

# Length of Suture #1
LBX_Sut1_Length_Left <- scanone(LBX_Left, pheno.col="Sut1_length_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Sut1_Length_Left)

# Length of Suture #2
LBX_Sut2_Length_Left <- scanone(LBX_Left, pheno.col="Sut2_length_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Sut2_Length_Left)
LBX_Sut2_Length_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="Sut2_length_left", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Sut2_Length_Left,perms=LBX_Sut2_Length_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peak - 0.024

# Length of Suture #3
LBX_Sut3_Length_Left <- scanone(LBX_Left, pheno.col="Sut3_length_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Sut3_Length_Left)
LBX_Sut3_Length_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="Sut3_length_left", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Sut3_Length_Left,perms=LBX_Sut3_Length_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peak - 0.008

# Length of Suture #4
LBX_Sut4_Length_Left <- scanone(LBX_Left, pheno.col="Sut4_length_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Sut4_Length_Left)

# Length of Suture #5
LBX_Sut5_Length_Left <- scanone(LBX_Left, pheno.col="Sut5_length_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Sut5_Length_Left)

# Length of Suture #6
LBX_Sut6_Length_Left <- scanone(LBX_Left, pheno.col="Sut6_length_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Sut6_Length_Left)

# Width of Arch #1
LBX_Arc1_Width_Left <- scanone(LBX_Left, pheno.col="Arc1_width_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Arc1_Width_Left)

# Width of Arch #2
LBX_Arc2_Width_Left <- scanone(LBX_Left, pheno.col="Arc2_width_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Arc2_Width_Left)

# Width of Arch #3
LBX_Arc3_Width_Left <- scanone(LBX_Left, pheno.col="Arc3_width_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Arc3_Width_Left)

# Width of Arch #4
LBX_Arc4_Width_Left <- scanone(LBX_Left, pheno.col="Arc4_width_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Arc4_Width_Left)

# Width of Arch #5
LBX_Arc5_Width_Left <- scanone(LBX_Left, pheno.col="Arc5_width_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Arc5_Width_Left)

# Left Length Total
LBX_Leftface_Length <- scanone(LBX_Left, pheno.col="Leftface_length", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Length)

# Noncutting edge length
LBX_Noncut_Edge_Length_Left <- scanone(LBX_Left, pheno.col="noncut_edge_length", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Noncut_Edge_Length_Left)
LBX_Noncut_Edge_Length_Left.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="noncut_edge_length", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Noncut_Edge_Length_Left,perms=LBX_Noncut_Edge_Length_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr2 - 1 peak - 0.024

# Rail Height
LBX_Rail_Height_Left <- scanone(LBX_Left, pheno.col="Intersect_to_top_dist_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Rail_Height_Left)

# Distance from Arch 2 to 3
LBX_Dist_Arc2_Arc3_Left <- scanone(LBX_Left, pheno.col="dist_arc2_arc3_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Dist_Arc2_Arc3_Left)

# Distance from Arch 3 to 4
LBX_Dist_Arc3_Arc4_Left <- scanone(LBX_Left, pheno.col="dist_arc3_arc4_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Dist_Arc3_Arc4_Left)

# Distance from Arch 4 to 5
LBX_Dist_Arc4_Arc5_Left <- scanone(LBX_Left, pheno.col="dist_arc4_arc5_left", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Dist_Arc4_Arc5_Left)

# Left Face Height #1
LBX_Leftface_Height1 <- scanone(LBX_Left, pheno.col="Leftface_height1", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Height1)

# Left Face Height #2
LBX_Leftface_Height2 <- scanone(LBX_Left, pheno.col="Leftface_height2", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Height2)

# Left Face Height #3
LBX_Leftface_Height3 <- scanone(LBX_Left, pheno.col="Leftface_height3", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Height3)

# Left Face Height #4
LBX_Leftface_Height4 <- scanone(LBX_Left, pheno.col="Leftface_height4", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Height4)

# Left Face Height #5
LBX_Leftface_Height5 <- scanone(LBX_Left, pheno.col="Leftface_height5", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Height5)
LBX_Leftface_Height5.scanone.perm<-scanone(LBX_Left,method="hk",pheno.col="Leftface_height5", addcovar=LBX_Left_CoVar_Body, n.perm=1000)
summary(LBX_Leftface_Height5,perms=LBX_Leftface_Height5.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peak - 0.007

# Left Face Height #6
LBX_Leftface_Height6 <- scanone(LBX_Left, pheno.col="Leftface_height6", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Height6)

# Left Face Height #7
LBX_Leftface_Height7 <- scanone(LBX_Left, pheno.col="Leftface_height7", method="hk", model="normal", addcovar=LBX_Left_CoVar_Body)
plot(LBX_Leftface_Height7)


## -------------------------------------------------------------------------- ##


# LBX Bottom
LBX_Bottom <- calc.genoprob(LBX_Bottom, step=0, error.prob = 0.01, map.function = "kosambi",stepwidth = "fixed")
LBX_Bottom_Fam <- as.numeric(pull.pheno(LBX_Bottom, pheno.col="Family"))

#families with one individual are not meaningful covariates; reduce to only those with >1
#first count number in each site
#test<-as.data.frame(cbind(LBX_Bottom$pheno$ID,LBX_Bottom_Fam))
#test%>%count(as.factor(LBX_Bottom_Fam))
#exclude families 12, 16,17 as covariates

LBX_Bottom_Fam1 <-as.numeric(LBX_Bottom_Fam == 1)
LBX_Bottom_Fam2 <- as.numeric (LBX_Bottom_Fam == 2)
LBX_Bottom_Fam3 <- as.numeric (LBX_Bottom_Fam == 3)
LBX_Bottom_Fam4 <- as.numeric (LBX_Bottom_Fam == 4)
LBX_Bottom_Fam5 <- as.numeric (LBX_Bottom_Fam == 5)
LBX_Bottom_Fam6 <- as.numeric (LBX_Bottom_Fam == 6)
LBX_Bottom_Fam7 <- as.numeric (LBX_Bottom_Fam == 7)
LBX_Bottom_Fam8 <- as.numeric (LBX_Bottom_Fam == 8)
LBX_Bottom_Fam9 <- as.numeric (LBX_Bottom_Fam == 9)
LBX_Bottom_Fam10 <- as.numeric (LBX_Bottom_Fam == 10)
LBX_Bottom_Fam11 <- as.numeric (LBX_Bottom_Fam == 11)
#LBX_Bottom_Fam12 <- as.numeric (LBX_Bottom_Fam == 12)
LBX_Bottom_Fam13 <- as.numeric (LBX_Bottom_Fam == 13)
LBX_Bottom_Fam14 <- as.numeric (LBX_Bottom_Fam == 14)
LBX_Bottom_Fam15 <- as.numeric (LBX_Bottom_Fam == 15)
#LBX_Bottom_Fam16 <- as.numeric (LBX_Bottom_Fam == 16)
#LBX_Bottom_Fam17 <- as.numeric (LBX_Bottom_Fam == 17)
LBX_Bottom_Fam18 <- as.numeric (LBX_Bottom_Fam == 18)
LBX_Bottom_Fam19 <- as.numeric (LBX_Bottom_Fam == 19)

LBX_Bottom_Fam_X <- cbind(LBX_Bottom_Fam1,LBX_Bottom_Fam2,LBX_Bottom_Fam3,LBX_Bottom_Fam4,LBX_Bottom_Fam5,LBX_Bottom_Fam6,LBX_Bottom_Fam7,LBX_Bottom_Fam8,LBX_Bottom_Fam9,LBX_Bottom_Fam10,LBX_Bottom_Fam11,LBX_Bottom_Fam13,LBX_Bottom_Fam14,LBX_Bottom_Fam15,LBX_Bottom_Fam18,LBX_Bottom_Fam19)
LBX_Bottom_Host <- as.numeric(pull.pheno(LBX_Bottom, pheno.col="WhiteChoice"))
LBX_Bottom_BodySize <- as.numeric(pull.pheno(LBX_Bottom, pheno.col="leg_length"))

LBX_Bottom_CoVar_Host <- cbind(LBX_Bottom_Host, LBX_Bottom_Fam_X)
LBX_Bottom_CoVar_Body <-cbind(LBX_Bottom_BodySize, LBX_Bottom_Fam_X)
LBX_Bottom_CoVar_All <-cbind (LBX_Bottom_Host, LBX_Bottom_BodySize, LBX_Bottom_Fam_X)

# Shape PCA Comp #1
LBX_Comp1_Bottom <- scanone(LBX_Bottom, pheno.col="Comp1", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp1_Bottom)

# Shape PCA Comp #2
LBX_Comp2_Bottom <- scanone(LBX_Bottom, pheno.col="Comp2", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp2_Bottom)

# Shape PCA Comp #3
LBX_Comp3_Bottom <- scanone(LBX_Bottom, pheno.col="Comp3", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp3_Bottom)

# Shape PCA Comp #4
LBX_Comp4_Bottom <- scanone(LBX_Bottom, pheno.col="Comp4", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp4_Bottom)

# Shape PCA Comp #5
LBX_Comp5_Bottom <- scanone(LBX_Bottom, pheno.col="Comp5", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp5_Bottom)

# Shape PCA Comp #6
LBX_Comp6_Bottom <- scanone(LBX_Bottom, pheno.col="Comp6", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp6_Bottom)

# Shape PCA Comp #7
LBX_Comp7_Bottom <- scanone(LBX_Bottom, pheno.col="Comp7", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp7_Bottom)

# Shape PCA Comp #8
LBX_Comp8_Bottom <- scanone(LBX_Bottom, pheno.col="Comp8", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp8_Bottom)

# Shape PCA Comp #9
LBX_Comp9_Bottom <- scanone(LBX_Bottom, pheno.col="Comp9", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp9_Bottom)

# Shape PCA Comp #10
LBX_Comp10_Bottom <- scanone(LBX_Bottom, pheno.col="Comp10", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp10_Bottom) 

# Shape PCA Comp #11
LBX_Comp11_Bottom <- scanone(LBX_Bottom, pheno.col="Comp11", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp11_Bottom)

# Shape PCA Comp #12
LBX_Comp12_Bottom <- scanone(LBX_Bottom, pheno.col="Comp12", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Comp12_Bottom)

# Centroid Size
LBX_Centroid_Size_Bottom <- scanone(LBX_Bottom, pheno.col="centroid_size_bottom", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Centroid_Size_Bottom)

# Length of the Cutting Edge
LBX_Cut_Edge_Length_Bottom <- scanone(LBX_Bottom, pheno.col="cut_edge_length_bot", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Cut_Edge_Length_Bottom)

# Length of the NonCutting Edge #1
LBX_Noncut_Edge_Length1_Bottom <- scanone(LBX_Bottom, pheno.col="noncut_edge_length_bot1", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Noncut_Edge_Length1_Bottom)

# Length of the NonCutting Edge #2
LBX_Noncut_Edge_Length2_Bottom <- scanone(LBX_Bottom, pheno.col="noncut_edge_length_bot2", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Noncut_Edge_Length2_Bottom)

# Distance Between Tips
LBX_Distance_to_Tip_Bottom <- scanone(LBX_Bottom, pheno.col="distance_to_tip", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Distance_to_Tip_Bottom)

# Interior Angle Between Tips
LBX_Inner_Angle_Bottom <- scanone(LBX_Bottom, pheno.col="inner_angle", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Inner_Angle_Bottom)

# Left Suture 8 Width
LBX_Left_Width_Sut8_Bottom <- scanone(LBX_Bottom, pheno.col="left_width_sut8", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Left_Width_Sut8_Bottom)

# Left Suture 7 Width
LBX_Left_Width_Sut7_Bottom <- scanone(LBX_Bottom, pheno.col="left_width_sut7", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Left_Width_Sut7_Bottom)

# Right Suture 8 Width
LBX_Right_Width_Sut8_Bottom <- scanone(LBX_Bottom, pheno.col="right_width_sut8", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Right_Width_Sut8_Bottom)

# Right Suture 7 Width
LBX_Right_Width_Sut7_Bottom <- scanone(LBX_Bottom, pheno.col="right_width_sut7", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Right_Width_Sut7_Bottom)

# Bottom Width
LBX_Bottom_Width <- scanone(LBX_Bottom, pheno.col="bottom_width", method="hk", model="normal", addcovar=LBX_Bottom_CoVar_Body)
plot(LBX_Bottom_Width)


## -------------------------------------------------------------------------- ##
## -------------------------------------------------------------------------- ##


## PBX Analysis ##
PBX_Right <- read.cross(format="csv",file="PBX_LanceRight_QTL_v2.csv",crosstype ="bc",na.strings="NA",genotypes=c("BB","AB"), estimate.map=FALSE)
PBX_Right <- jittermap(PBX_Right)
PBX_Left <- read.cross(format="csv",file="PBX_LanceLeft_QTL_v2.csv",crosstype ="bc",na.strings="NA",genotypes=c("BB","AB"), estimate.map=FALSE)
PBX_Left <- jittermap(PBX_Left)
PBX_Bottom <- read.cross(format="csv",file="PBX_LanceBottom_QTL_v2.csv",crosstype ="bc",na.strings="NA",genotypes=c("BB","AB"), estimate.map=FALSE)
PBX_Bottom <- jittermap(PBX_Bottom)

# PBX Right
PBX_Right <- calc.genoprob(PBX_Right, step=0, error.prob = 0.01, map.function = "kosambi",stepwidth = "fixed")
PBX_Right_Fam <- as.numeric(pull.pheno(PBX_Right, pheno.col="Family"))

#families with one individual are not meaningful covariates; reduce to only those with >1
#first count number in each site
#test<-as.data.frame(cbind(PBX_Right$pheno$ID,PBX_Right_Fam))
#test%>%count(as.factor(PBX_Right_Fam))
#exclude families 5 covariate

PBX_Right_Fam1 <-as.numeric(PBX_Right_Fam == 1)
PBX_Right_Fam2 <- as.numeric (PBX_Right_Fam == 2)
PBX_Right_Fam3 <- as.numeric (PBX_Right_Fam == 3)
PBX_Right_Fam4 <- as.numeric (PBX_Right_Fam == 4)
#PBX_Right_Fam5 <- as.numeric (PBX_Right_Fam == 5)
PBX_Right_Fam6 <- as.numeric (PBX_Right_Fam == 6)
PBX_Right_Fam7 <- as.numeric (PBX_Right_Fam == 7)
PBX_Right_Fam8 <- as.numeric (PBX_Right_Fam == 8)
PBX_Right_Fam9 <- as.numeric (PBX_Right_Fam == 9)
PBX_Right_Fam10 <- as.numeric (PBX_Right_Fam == 10)

PBX_Right_Fam_X <- cbind(PBX_Right_Fam1,PBX_Right_Fam2,PBX_Right_Fam3,PBX_Right_Fam4,PBX_Right_Fam6,PBX_Right_Fam7,PBX_Right_Fam8,PBX_Right_Fam9,PBX_Right_Fam10)
PBX_Right_Host <- as.numeric(pull.pheno(PBX_Right, pheno.col="WhiteChoice"))
PBX_Right_BodySize <- as.numeric(pull.pheno(PBX_Right, pheno.col="leg_length"))

PBX_Right_CoVar_Host <- cbind(PBX_Right_Host, PBX_Right_Fam_X)
PBX_Right_CoVar_Body <-cbind(PBX_Right_BodySize, PBX_Right_Fam_X)
PBX_Right_CoVar_All <-cbind (PBX_Right_Host, PBX_Right_BodySize, PBX_Right_Fam_X)

#Shape PCA Comp #1
PBX_Comp1_Right <- scanone(PBX_Right, pheno.col="Comp1", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp1_Right)
PBX_Comp1_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Comp1", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Comp1_Right,perms=PBX_Comp1_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr4 - 1 peak - 0.001

# Shape PCA Comp #2
PBX_Comp2_Right <- scanone(PBX_Right, pheno.col="Comp2", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp2_Right)

# Shape PCA Comp #3
PBX_Comp3_Right <- scanone(PBX_Right, pheno.col="Comp3", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp3_Right)

# Shape PCA Comp #4
PBX_Comp4_Right <- scanone(PBX_Right, pheno.col="Comp4", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp4_Right)

# Shape PCA Comp #5
PBX_Comp5_Right <- scanone(PBX_Right, pheno.col="Comp5", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp5_Right)
PBX_Comp5_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Comp5", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Comp5_Right,perms=PBX_Comp5_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr1 & 2 - 2 peaks - 0.000 to 0.033

# Shape PCA Comp #6
PBX_Comp6_Right <- scanone(PBX_Right, pheno.col="Comp6", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp6_Right)

# Shape PCA Comp #7
PBX_Comp7_Right <- scanone(PBX_Right, pheno.col="Comp7", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp7_Right)
PBX_Comp7_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Comp7", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Comp7_Right,perms=PBX_Comp7_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr2 - 1 peaks - 0 

# Shape PCA Comp #8
PBX_Comp8_Right <- scanone(PBX_Right, pheno.col="Comp8", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp8_Right)

# Shape PCA Comp #9
PBX_Comp9_Right <- scanone(PBX_Right, pheno.col="Comp9", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp9_Right)

# Shape PCA Comp #10
PBX_Comp10_Right <- scanone(PBX_Right, pheno.col="Comp10", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp10_Right)

# Shape PCA Comp #11
PBX_Comp11_Right <- scanone(PBX_Right, pheno.col="Comp11", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp11_Right)
PBX_Comp11_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Comp11", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Comp11_Right,perms=PBX_Comp11_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr1 - 1 peaks - 0.034

# Shape PCA Comp #12
PBX_Comp12_Right <- scanone(PBX_Right, pheno.col="Comp12", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Comp12_Right)

# Centroid Size
PBX_Centroid_Size_Right <- scanone(PBX_Right, pheno.col="centroid_size_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Centroid_Size_Right)
PBX_Centroid_Size_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="centroid_size_right", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Centroid_Size_Right,perms=PBX_Centroid_Size_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr1 & 4 - 2 peaks - 0.010 to 0.017

# Cuticular Window Length
PBX_Cutwindow_Length_Right <- scanone(PBX_Right, pheno.col="Cutwindow_length_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Cutwindow_Length_Right) #!!!
PBX_Cutwindow_Length_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Cutwindow_length_right", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Cutwindow_Length_Right,perms=PBX_Cutwindow_Length_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr1 - 1 peaks - 0.009

# Distance from Cuticular window to Tip #1
PBX_Window_to_Edge1_Right <- scanone(PBX_Right, pheno.col="window_to_edge1", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Window_to_Edge1_Right) # !!!
PBX_Window_to_Edge1_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="window_to_edge1", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Window_to_Edge1_Right,perms=PBX_Window_to_Edge1_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr3 - 1 peak - 0.012

# Suture #1 Length
PBX_Sut1_Length_Right <- scanone(PBX_Right, pheno.col="Sut1_length_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Sut1_Length_Right)

# Suture #2 Length
PBX_Sut2_Length_Right <- scanone(PBX_Right, pheno.col="Sut2_length_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Sut2_Length_Right)

# Suture #3 Length
PBX_Sut3_Length_Right <- scanone(PBX_Right, pheno.col="Sut3_length_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Sut3_Length_Right)

# Suture #4 Length
PBX_Sut4_Length_Right <- scanone(PBX_Right, pheno.col="Sut4_length_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Sut4_Length_Right)

# Suture #5 Length
PBX_Sut5_Length_Right <- scanone(PBX_Right, pheno.col="Sut5_length_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Sut5_Length_Right) # !!!
PBX_Sut5_Length_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Sut5_length_right", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Sut5_Length_Right,perms=PBX_Sut5_Length_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr5 - 1 peak - 0.01

# Suture #6 Length
PBX_Sut6_Length_Right <- scanone(PBX_Right, pheno.col="Sut6_length_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Sut6_Length_Right)

# Arch #1 Width
PBX_Arc1_Width_Right <- scanone(PBX_Right, pheno.col="Arc1_width_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Arc1_Width_Right) # ???
PBX_Arc1_Width_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Arc1_width_right", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Arc1_Width_Right,perms=PBX_Arc1_Width_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr4 - 1 peak - 0.022

# Arch #2 Width
PBX_Arc2_Width_Right <- scanone(PBX_Right, pheno.col="Arc2_width_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Arc2_Width_Right)

# Arch #3 Width
PBX_Arc3_Width_Right <- scanone(PBX_Right, pheno.col="Arc3_width_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Arc3_Width_Right)

# Arch #4 Width
PBX_Arc4_Width_Right <- scanone(PBX_Right, pheno.col="Arc4_width_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Arc4_Width_Right)

# Arch #5 Width
PBX_Arc5_Width_Right <- scanone(PBX_Right, pheno.col="Arc5_width_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Arc5_Width_Right)

# Arch #6 Width
PBX_Arc6_Width_Right <- scanone(PBX_Right, pheno.col="Arc6_width_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Arc6_Width_Right)

# Total Length
PBX_Rightface_Length <- scanone(PBX_Right, pheno.col="Rightface_len", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Rightface_Length)
PBX_Rightface_Length.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Rightface_len", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Rightface_Length,perms=PBX_Rightface_Length.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr1 & 3 - 2 peaks - 0 to 0.023

# Length of the Cutting Edge
PBX_Cut_Edge_Length <- scanone(PBX_Right, pheno.col="cut_edge_length", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Cut_Edge_Length)
PBX_Cut_Edge_Length.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="cut_edge_length", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Cut_Edge_Length,perms=PBX_Cut_Edge_Length.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr3 - 1 peak - 0.003

# Rail Height
PBX_Rail_Height_Right <- scanone(PBX_Right, pheno.col="Intersect_to_top_dist_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Rail_Height_Right)

# Distance from Arch 2 to 3
PBX_Dist_Arc2_Arc3_Right <- scanone(PBX_Right, pheno.col="dist_arc2_arc3_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Dist_Arc2_Arc3_Right)

# Distance from Arch 3 to 4
PBX_Dist_Arc3_Arc4_Right <- scanone(PBX_Right, pheno.col="dist_arc3_arc4_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Dist_Arc3_Arc4_Right)

# Distance from Arch 4 to 5
PBX_Dist_Arc4_Arc5_Right <- scanone(PBX_Right, pheno.col="dist_arc4_arc5_right", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Dist_Arc4_Arc5_Right) 
PBX_Dist_Arc4_Arc5_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="dist_arc4_arc5_right", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Dist_Arc4_Arc5_Right,perms=PBX_Dist_Arc4_Arc5_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr 4 - 1 peak - 0.005

# Right Face Height #1
PBX_RightFace_Height1 <- scanone(PBX_Right, pheno.col="Rightface_height1", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_RightFace_Height1)

# Right Face Height #2
PBX_RightFace_Height2 <- scanone(PBX_Right, pheno.col="Rightface_height2", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_RightFace_Height2)

# Right Face Height #3
PBX_RightFace_Height3 <- scanone(PBX_Right, pheno.col="Rightface_height3", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_RightFace_Height3)

# Right Face Height #4
PBX_RightFace_Height4 <- scanone(PBX_Right, pheno.col="Rightface_height4", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_RightFace_Height4)

# Right Face Height #5
PBX_RightFace_Height5 <- scanone(PBX_Right, pheno.col="Rightface_height5", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_RightFace_Height5)
PBX_RightFace_Height5.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="Rightface_height5", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_RightFace_Height5,perms=PBX_RightFace_Height5.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr2 - 1 peak - 0.041

# Right Face Height #6
PBX_RightFace_Height6 <- scanone(PBX_Right, pheno.col="Rightface_height6", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_RightFace_Height6)

# Right Face Height #7
PBX_RightFace_Height7 <- scanone(PBX_Right, pheno.col="Rightface_height7", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_RightFace_Height7)

# Depth of the Cutting Edge #1
PBX_Cutting_Depth1 <- scanone(PBX_Right, pheno.col="cutting_depth1", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Cutting_Depth1)

# Depth of the Cutting Edge #2
PBX_Cutting_Depth2 <- scanone(PBX_Right, pheno.col="cutting_depth2", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Cutting_Depth2)

# Right Face Rail Length
PBX_Rail_Length_Right <- scanone(PBX_Right, pheno.col="rail_length", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Rail_Length_Right)
PBX_Rail_Length_Right.scanone.perm <- scanone(PBX_Right,method="hk",pheno.col="rail_length", addcovar=PBX_Right_CoVar_Body, n.perm=1000)
summary(PBX_Rail_Length_Right,perms=PBX_Rail_Length_Right.scanone.perm,alpha=0.05, pvalues=TRUE) #SIG - Chr1 & 3 - 2 peaks - 0 to 0.026

# Distance from Bottom of the Cuticular Window to the Rail
PBX_Window_to_Rail_Right <- scanone(PBX_Right, pheno.col="window_to_rail", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Window_to_Rail_Right)

# Reveresed Asymetry of the Cutting Edge
PBX_Cut_Edge_Aysmmetry <- scanone(PBX_Right, pheno.col="cut_edge_aysmmetry", method="hk", model="normal", addcovar=PBX_Right_CoVar_Body)
plot(PBX_Cut_Edge_Aysmmetry)


## -------------------------------------------------------------------------- ##


# PBX Left
PBX_Left <- calc.genoprob(PBX_Left, step=0, error.prob = 0.01, map.function = "kosambi",stepwidth = "fixed")
PBX_Left_Fam <- as.numeric(pull.pheno(PBX_Left, pheno.col="Family"))

#families with one individual are not meaningful covariates; reduce to only those with >1
#first count number in each site
test<-as.data.frame(cbind(PBX_Left$pheno$ID,PBX_Left_Fam))
test%>%count(as.factor(PBX_Left_Fam))
#exclude families 5 covariate

PBX_Left_Fam1 <-as.numeric(PBX_Left_Fam == 1)
PBX_Left_Fam2 <- as.numeric (PBX_Left_Fam == 2)
PBX_Left_Fam3 <- as.numeric (PBX_Left_Fam == 3)
PBX_Left_Fam4 <- as.numeric (PBX_Left_Fam == 4)
#PBX_Left_Fam5 <- as.numeric (PBX_Left_Fam == 5)
PBX_Left_Fam6 <- as.numeric (PBX_Left_Fam == 6)
PBX_Left_Fam7 <- as.numeric (PBX_Left_Fam == 7)
PBX_Left_Fam8 <- as.numeric (PBX_Left_Fam == 8)
PBX_Left_Fam9 <- as.numeric (PBX_Left_Fam == 9)
PBX_Left_Fam10 <- as.numeric (PBX_Left_Fam == 10)

PBX_Left_Fam_X <- cbind(PBX_Left_Fam1,PBX_Left_Fam2,PBX_Left_Fam3,PBX_Left_Fam4,PBX_Left_Fam6,PBX_Left_Fam7,PBX_Left_Fam8,PBX_Left_Fam9,PBX_Left_Fam10)
PBX_Left_Host <- as.numeric(pull.pheno(PBX_Left, pheno.col="WhiteChoice"))
PBX_Left_BodySize <- as.numeric(pull.pheno(PBX_Left, pheno.col="leg_length"))

PBX_Left_CoVar_Host <- cbind(PBX_Left_Host, PBX_Left_Fam_X)
PBX_Left_CoVar_Body <-cbind(PBX_Left_BodySize, PBX_Left_Fam_X)
PBX_Left_CoVar_All <-cbind (PBX_Left_Host, PBX_Left_BodySize, PBX_Left_Fam_X)

#Shape PCA Comp #1
PBX_Comp1_Left <- scanone(PBX_Left, pheno.col="Comp1", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp1_Left)
PBX_Comp1_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Comp1", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Comp1_Left,perms=PBX_Comp1_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr5 - 1 peak - 0.024

# Shape PCA Comp #2
PBX_Comp2_Left <- scanone(PBX_Left, pheno.col="Comp2", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp2_Left)
PBX_Comp2_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Comp2", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Comp2_Left,perms=PBX_Comp2_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peak - 0.031

# Shape PCA Comp #3
PBX_Comp3_Left <- scanone(PBX_Left, pheno.col="Comp3", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp3_Left)

# Shape PCA Comp #4
PBX_Comp4_Left <- scanone(PBX_Left, pheno.col="Comp4", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp4_Left)
PBX_Comp4_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Comp4", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Comp4_Left,perms=PBX_Comp4_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peak - 0.001

# Shape PCA Comp #5
PBX_Comp5_Left <- scanone(PBX_Left, pheno.col="Comp5", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp5_Left)

# Shape PCA Comp #6
PBX_Comp6_Left <- scanone(PBX_Left, pheno.col="Comp6", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp6_Left)

# Shape PCA Comp #7
PBX_Comp7_Left <- scanone(PBX_Left, pheno.col="Comp7", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp7_Left)

# Shape PCA Comp #8
PBX_Comp8_Left <- scanone(PBX_Left, pheno.col="Comp8", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp8_Left)
PBX_Comp8_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Comp8", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Comp8_Left,perms=PBX_Comp8_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peak - 0.029

# Shape PCA Comp #9
PBX_Comp9_Left <- scanone(PBX_Left, pheno.col="Comp9", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp9_Left)

# Shape PCA Comp #10
PBX_Comp10_Left <- scanone(PBX_Left, pheno.col="Comp10", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp10_Left)

# Shape PCA Comp #11
PBX_Comp11_Left <- scanone(PBX_Left, pheno.col="Comp11", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp11_Left)

# Shape PCA Comp #12
PBX_Comp12_Left <- scanone(PBX_Left, pheno.col="Comp12", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Comp12_Left)

# Centroid Size
PBX_Centroid_Size_Left <- scanone(PBX_Left, pheno.col="centroid_size_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Centroid_Size_Left)
PBX_Centroid_Size_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="centroid_size_left", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Centroid_Size_Left,perms=PBX_Centroid_Size_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 & 3 - 2 peaks - 0.008 to 0.011 

# Cuticular Window Length
PBX_Cutwindow_Length_Left <- scanone(PBX_Left, pheno.col="Cutwindow_length_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Cutwindow_Length_Left)
PBX_Cutwindow_Length_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Cutwindow_length_left", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Cutwindow_Length_Left,perms=PBX_Cutwindow_Length_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 & 3 - 2 peaks - 0.002 to 0.028

# Length of Suture #1
PBX_Sut1_Length_Left <- scanone(PBX_Left, pheno.col="Sut1_length_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Sut1_Length_Left)
PBX_Sut1_Length_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Sut1_length_left", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Sut1_Length_Left,perms=PBX_Sut1_Length_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peaks - 0

# Length of Suture #2
PBX_Sut2_Length_Left <- scanone(PBX_Left, pheno.col="Sut2_length_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Sut2_Length_Left)
PBX_Sut2_Length_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Sut2_length_left", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Sut2_Length_Left,perms=PBX_Sut2_Length_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peak - 0.031

# Length of Suture #3
PBX_Sut3_Length_Left <- scanone(PBX_Left, pheno.col="Sut3_length_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Sut3_Length_Left)

# Length of Suture #4
PBX_Sut4_Length_Left <- scanone(PBX_Left, pheno.col="Sut4_length_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Sut4_Length_Left)

# Length of Suture #5
PBX_Sut5_Length_Left <- scanone(PBX_Left, pheno.col="Sut5_length_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Sut5_Length_Left)

# Length of Suture #6
PBX_Sut6_Length_Left <- scanone(PBX_Left, pheno.col="Sut6_length_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Sut6_Length_Left)

# Width of Arch #1
PBX_Arc1_Width_Left <- scanone(PBX_Left, pheno.col="Arc1_width_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Arc1_Width_Left)

# Width of Arch #2
PBX_Arc2_Width_Left <- scanone(PBX_Left, pheno.col="Arc2_width_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Arc2_Width_Left)

# Width of Arch #3
PBX_Arc3_Width_Left <- scanone(PBX_Left, pheno.col="Arc3_width_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Arc3_Width_Left)

# Width of Arch #4
PBX_Arc4_Width_Left <- scanone(PBX_Left, pheno.col="Arc4_width_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Arc4_Width_Left)

# Width of Arch #5
PBX_Arc5_Width_Left <- scanone(PBX_Left, pheno.col="Arc5_width_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Arc5_Width_Left)
PBX_Arc5_Width_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Arc5_width_left", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Arc5_Width_Left,perms=PBX_Arc5_Width_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr2 - 1 peak - 0.007

# Left Length Total
PBX_Leftface_Length <- scanone(PBX_Left, pheno.col="Leftface_length", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Leftface_Length)
PBX_Leftface_Length.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Leftface_length", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Leftface_Length,perms=PBX_Leftface_Length.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peak - 0.004

# Noncutting edge length
PBX_Noncut_Edge_Length_Left <- scanone(PBX_Left, pheno.col="noncut_edge_length", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Noncut_Edge_Length_Left)
PBX_Noncut_Edge_Length_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="noncut_edge_length", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Noncut_Edge_Length_Left,perms=PBX_Noncut_Edge_Length_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1, 3 & 5 - 3 peaks - 0 to 0.029

# Rail Height
PBX_Rail_Height_Left <- scanone(PBX_Left, pheno.col="Intersect_to_top_dist_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Rail_Height_Left)

# Distance from Arch 2 to 3
PBX_Dist_Arc2_Arc3_Left <- scanone(PBX_Left, pheno.col="dist_arc2_arc3_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Dist_Arc2_Arc3_Left)
PBX_Dist_Arc2_Arc3_Left.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="dist_arc2_arc3_left", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Dist_Arc2_Arc3_Left,perms=PBX_Dist_Arc2_Arc3_Left.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peaks - 0.001

# Distance from Arch 3 to 4
PBX_Dist_Arc3_Arc4_Left <- scanone(PBX_Left, pheno.col="dist_arc3_arc4_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Dist_Arc3_Arc4_Left)

# Distance from Arch 4 to 5
PBX_Dist_Arc4_Arc5_Left <- scanone(PBX_Left, pheno.col="dist_arc4_arc5_left", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Dist_Arc4_Arc5_Left)

# Left Face Height #1
PBX_Leftface_Height1 <- scanone(PBX_Left, pheno.col="Leftface_height1", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Leftface_Height1)
PBX_Leftface_Height1.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Leftface_height1", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Leftface_Height1,perms=PBX_Leftface_Height1.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peaks - 0.006

# Left Face Height #2
PBX_Leftface_Height2 <- scanone(PBX_Left, pheno.col="Leftface_height2", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Leftface_Height2)
PBX_Leftface_Height2.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Leftface_height2", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Leftface_Height2,perms=PBX_Leftface_Height2.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peaks - 0.005

# Left Face Height #3
PBX_Leftface_Height3 <- scanone(PBX_Left, pheno.col="Leftface_height3", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Leftface_Height3)
PBX_Leftface_Height3.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Leftface_height3", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Leftface_Height3,perms=PBX_Leftface_Height3.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr1 - 1 peaks - 0.002

# Left Face Height #4
PBX_Leftface_Height4 <- scanone(PBX_Left, pheno.col="Leftface_height4", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Leftface_Height4)

# Left Face Height #5
PBX_Leftface_Height5 <- scanone(PBX_Left, pheno.col="Leftface_height5", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)

# Left Face Height #6
PBX_Leftface_Height6 <- scanone(PBX_Left, pheno.col="Leftface_height6", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Leftface_Height6)
PBX_Leftface_Height6.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Leftface_height6", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Leftface_Height6,perms=PBX_Leftface_Height6.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peaks - 0.007

# Left Face Height #7
PBX_Leftface_Height7 <- scanone(PBX_Left, pheno.col="Leftface_height7", method="hk", model="normal", addcovar=PBX_Left_CoVar_Body)
plot(PBX_Leftface_Height7)
PBX_Leftface_Height7.scanone.perm<-scanone(PBX_Left,method="hk",pheno.col="Leftface_height7", addcovar=PBX_Left_CoVar_Body, n.perm=1000)
summary(PBX_Leftface_Height7,perms=PBX_Leftface_Height7.scanone.perm,alpha=0.05, pvalues=TRUE) # SIG - Chr4 - 1 peaks - 0.007


## -------------------------------------------------------------------------- ##


# PBX Bottom
PBX_Bottom <- calc.genoprob(PBX_Bottom, step=0, error.prob = 0.01, map.function = "kosambi",stepwidth = "fixed")
PBX_Bottom_Fam <- as.numeric(pull.pheno(PBX_Bottom, pheno.col="Family"))

#families with one individual are not meaningful covariates; reduce to only those with >1
#first count number in each site
#test<-as.data.frame(cbind(PBX_Bottom$pheno$ID,PBX_Bottom_Fam))
#test%>%count(as.factor(PBX_Bottom_Fam))
#exclude families 5 covariate

PBX_Bottom_Fam1 <-as.numeric(PBX_Bottom_Fam == 1)
PBX_Bottom_Fam2 <- as.numeric (PBX_Bottom_Fam == 2)
PBX_Bottom_Fam3 <- as.numeric (PBX_Bottom_Fam == 3)
PBX_Bottom_Fam4 <- as.numeric (PBX_Bottom_Fam == 4)
#PBX_Bottom_Fam5 <- as.numeric (PBX_Bottom_Fam == 5)
PBX_Bottom_Fam6 <- as.numeric (PBX_Bottom_Fam == 6)
PBX_Bottom_Fam7 <- as.numeric (PBX_Bottom_Fam == 7)
PBX_Bottom_Fam8 <- as.numeric (PBX_Bottom_Fam == 8)
PBX_Bottom_Fam9 <- as.numeric (PBX_Bottom_Fam == 9)
PBX_Bottom_Fam10 <- as.numeric (PBX_Bottom_Fam == 10)

PBX_Bottom_Fam_X <- cbind(PBX_Bottom_Fam1,PBX_Bottom_Fam2,PBX_Bottom_Fam3,PBX_Bottom_Fam4,PBX_Bottom_Fam6,PBX_Bottom_Fam7,PBX_Bottom_Fam8,PBX_Bottom_Fam9,PBX_Bottom_Fam10)
PBX_Bottom_Host <- as.numeric(pull.pheno(PBX_Bottom, pheno.col="WhiteChoice"))
PBX_Bottom_BodySize <- as.numeric(pull.pheno(PBX_Bottom, pheno.col="leg_length"))

PBX_Bottom_CoVar_Host <- cbind(PBX_Bottom_Host, PBX_Bottom_Fam_X)
PBX_Bottom_CoVar_Body <-cbind(PBX_Bottom_BodySize, PBX_Bottom_Fam_X)
PBX_Bottom_CoVar_All <-cbind (PBX_Bottom_Host, PBX_Bottom_BodySize, PBX_Bottom_Fam_X)

# Shape PCA Comp #1
PBX_Comp1_Bottom <- scanone(PBX_Bottom, pheno.col="Comp1", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp1_Bottom)

# Shape PCA Comp #2
PBX_Comp2_Bottom <- scanone(PBX_Bottom, pheno.col="Comp2", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp2_Bottom)

# Shape PCA Comp #3
PBX_Comp3_Bottom <- scanone(PBX_Bottom, pheno.col="Comp3", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp3_Bottom)

# Shape PCA Comp #4
PBX_Comp4_Bottom <- scanone(PBX_Bottom, pheno.col="Comp4", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp4_Bottom)

# Shape PCA Comp #5
PBX_Comp5_Bottom <- scanone(PBX_Bottom, pheno.col="Comp5", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp5_Bottom)

# Shape PCA Comp #6
PBX_Comp6_Bottom <- scanone(PBX_Bottom, pheno.col="Comp6", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp6_Bottom)

# Shape PCA Comp #7
PBX_Comp7_Bottom <- scanone(PBX_Bottom, pheno.col="Comp7", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp7_Bottom)

# Shape PCA Comp #8
PBX_Comp8_Bottom <- scanone(PBX_Bottom, pheno.col="Comp8", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp8_Bottom)

# Shape PCA Comp #9
PBX_Comp9_Bottom <- scanone(PBX_Bottom, pheno.col="Comp9", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp9_Bottom)

# Shape PCA Comp #10
PBX_Comp10_Bottom <- scanone(PBX_Bottom, pheno.col="Comp10", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp10_Bottom) 

# Shape PCA Comp #11
PBX_Comp11_Bottom <- scanone(PBX_Bottom, pheno.col="Comp11", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp11_Bottom)

# Shape PCA Comp #12
PBX_Comp12_Bottom <- scanone(PBX_Bottom, pheno.col="Comp12", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Comp12_Bottom)

# Centroid Size
PBX_Centroid_Size_Bottom <- scanone(PBX_Bottom, pheno.col="centroid_size_bottom", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Centroid_Size_Bottom)

# Length of the Cutting Edge
PBX_Cut_Edge_Length_Bottom <- scanone(PBX_Bottom, pheno.col="cut_edge_length_bot", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Cut_Edge_Length_Bottom)

# Length of the NonCutting Edge #1
PBX_Noncut_Edge_Length1_Bottom <- scanone(PBX_Bottom, pheno.col="noncut_edge_length_bot1", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Noncut_Edge_Length1_Bottom)

# Length of the NonCutting Edge #2
PBX_Noncut_Edge_Length2_Bottom <- scanone(PBX_Bottom, pheno.col="noncut_edge_length_bot2", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Noncut_Edge_Length2_Bottom)

# Distance Between Tips
PBX_Distance_to_Tip_Bottom <- scanone(PBX_Bottom, pheno.col="distance_to_tip", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Distance_to_Tip_Bottom)

# Interior Angle Between Tips
PBX_Inner_Angle_Bottom <- scanone(PBX_Bottom, pheno.col="inner_angle", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Inner_Angle_Bottom)

# Left Suture 8 Width
PBX_Left_Width_Sut8_Bottom <- scanone(PBX_Bottom, pheno.col="left_width_sut8", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Left_Width_Sut8_Bottom)

# Left Suture 7 Width
PBX_Left_Width_Sut7_Bottom <- scanone(PBX_Bottom, pheno.col="left_width_sut7", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Left_Width_Sut7_Bottom)

# Right Suture 8 Width
PBX_Right_Width_Sut8_Bottom <- scanone(PBX_Bottom, pheno.col="right_width_sut8", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Right_Width_Sut8_Bottom)

# Right Suture 7 Width
PBX_Right_Width_Sut7_Bottom <- scanone(PBX_Bottom, pheno.col="right_width_sut7", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Right_Width_Sut7_Bottom)

# Bottom Width
PBX_Bottom_Width <- scanone(PBX_Bottom, pheno.col="bottom_width", method="hk", model="normal", addcovar=PBX_Bottom_CoVar_Body)
plot(PBX_Bottom_Width)
