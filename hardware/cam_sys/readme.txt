1.编译前激活tobacco_env，修改CMakeLists.txt中Python_ROOT_DIR和pybind11_DIR
2.创建build文件夹（若有可删除重建或清空）

3.进入build文件夹，执行cmake .. && make

4.执行3d_capture.py获取3d相机图片（两张，主码流+第四码流），执行scan_capture.py获取扫码相机图片（一张，主码流）
5.存储路径为build文件夹下的output/任务号/库位号/3d_camera（scan_camera）

PS:请注意修改两个py文件中的相机IP、PORT、账号和密码，如果已执行cmake ..，请直接修改build文件夹下的py文件，修改外层无效，除非删除或清空build，重新cmake ..
