12 models, 5 fold runs each, balanced accuracy on the test fold.
Checks: 1 of 12 models have scores that are not normal (Shapiro-Wilk); equal spread across models, Levene p=0.946.
Kruskal-Wallis (method of the article): statistic 23.486, p=0.0151; the models differ. Pairs: Conover-Iman with Holm-Sidak.
Friedman (paired check): statistic 23.000, p=0.0177; the models differ. Nemenyi critical difference 7.45 rank units (ranks go from 1 to 12).
CNN against transformer, all fold scores of each family together (35 and 25 scores): median 90.1% against 90.0%, Mann-Whitney p=0.4534.

- best cnn: resnet50 (91.2%); cannot be told apart from: densenet121, convnext_large, efficientnet_b3, vgg16, efficientnet_b0, mobilenetv2
- best transformer: swin_base_patch4_window7_224 (91.3%); cannot be told apart from: pit_s_distilled_224, swin_tiny_patch4_window7_224, coat_lite_small
- best overall: swin_base_patch4_window7_224; better than (Conover): vit_small_patch16_384; better than (Nemenyi, paired): vit_small_patch16_384
