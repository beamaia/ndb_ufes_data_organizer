12 models, 5 fold runs each, balanced accuracy on the test fold.
Checks: 0 of 12 models have scores that are not normal (Shapiro-Wilk); equal spread across models, Levene p=0.705.
Kruskal-Wallis (method of the article): statistic 22.191, p=0.0229; the models differ. Pairs: Conover-Iman with Holm-Sidak.
Friedman (paired check): statistic 22.169, p=0.0231; the models differ. Nemenyi critical difference 7.45 rank units (ranks go from 1 to 12).
CNN against transformer, all fold scores of each family together (35 and 25 scores): median 56.3% against 59.8%, Mann-Whitney p=0.0022.

- best cnn: vgg16 (58.7%); cannot be told apart from: mobilenetv2, convnext_large, densenet121, efficientnet_b0, efficientnet_b3, resnet50
- best transformer: swin_tiny_patch4_window7_224 (61.4%); cannot be told apart from: vit_small_patch16_384, pit_s_distilled_224, coat_lite_small, swin_base_patch4_window7_224
- best overall: swin_tiny_patch4_window7_224; better than (Conover): efficientnet_b3, resnet50; better than (Nemenyi, paired): efficientnet_b3, resnet50
