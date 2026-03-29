/*
 * @Author: big box big box@qq.com
 * @Date: 2025-12-03 22:09:19
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-12-11 22:04:07
 * @FilePath: /cam_sys_3/src/pybind_cam_control.cpp
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
#include "CamController.h"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"  // 用于支持 STL 容器

namespace py = pybind11;

PYBIND11_MODULE(camera_api, m) {
  py::class_<CamController>(m, "CamController")
      .def(py::init<>())
      .def("login", &CamController::login, py::arg("deviceAddress"),
           py::arg("port"), py::arg("userName"), py::arg("password"))
      .def("logout", &CamController::logout)
      .def("startRealPlay", &CamController::startRealPlay, py::arg("channel"),
           py::arg("streamType"), py::arg("linkMode"), py::arg("blocked"))
      .def("stopRealPlay", &CamController::stopRealPlay)
      .def("getCapture", &CamController::getCapture)
      .def("setTaskInfo", &CamController::setTaskInfo, py::arg("task_id"),
           py::arg("bin_code"))
      .def("setCameraType", &CamController::setCameraType,
           py::arg("camera_type"));

  //  // 绑定无参版本：使用函数指针类型转换明确指定
  //  .def("doGetCapturePicture_JPG",
  //       static_cast<int (CameraController::*)()>(
  //           &CameraController::doGetCapturePicture_JPG))

  //  // 绑定有参版本：使用函数指针类型转换明确指定
  //  .def("doGetCapturePicture_JPG_Param",
  //       static_cast<int (CameraController::*)(
  //           const std::string&, const std::string&, const std::string&,
  //           const
  //           std::string&)>(&CameraController::doGetCapturePicture_JPG),
  //       py::arg("basePath"), py::arg("taskId"), py::arg("binCode"),
  //       py::arg("cameraType"));

  m.doc() = "Camera controller module";  // 可选的模块文档
}
