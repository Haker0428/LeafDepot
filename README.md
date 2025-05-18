# LeafDepot
本项目致力于开发一套自动识别烟箱数量的视觉算法，用于烟草仓储场景，替代人工统计方式，从而提升仓储效率并减少差错率。

主要功能：

基于计算机视觉的烟箱数量自动识别

适应不同堆叠方式和光照条件

提供高准确率和实时识别能力

可与仓储管理系统（WMS）对接使用

# How to Use

* 克隆仓库后，创建环境：
```
conda env create -f environment.yml
```

* 激活环境
```
conda activate tobacco-env
```

后续如果有更新python库，在根目录使用如下命令:
```
conda env export --from-history > environment.yml
```