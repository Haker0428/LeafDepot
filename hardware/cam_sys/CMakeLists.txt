cmake_minimum_required(VERSION 3.16)
project(cam_sys)

# 设置C++标准
set(CMAKE_CXX_STANDARD 11)

# 更好的RPATH处理
set(CMAKE_BUILD_RPATH_USE_ORIGIN TRUE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

# 添加可执行文件
add_library(${PROJECT_NAME} SHARED
    src/CamController.cpp 
)

# 设置RPATH - 使用相对路径
set_target_properties(${PROJECT_NAME} PROPERTIES
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "$ORIGIN/../lib:$ORIGIN/../lib/HCNetSDKCom"
    SKIP_BUILD_RPATH FALSE
)

# 包含头文件目录
target_include_directories(${PROJECT_NAME} PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

# 链接库目录
target_link_directories(${PROJECT_NAME} PUBLIC
    ${CMAKE_SOURCE_DIR}/lib
    ${CMAKE_SOURCE_DIR}/lib/HCNetSDKCom
)

# 查找库文件
find_library(SSL_LIB
    NAMES libssl.so.1.1 ssl
    PATHS ${CMAKE_SOURCE_DIR}/lib
    NO_DEFAULT_PATH
    REQUIRED
)
find_library(OPENAL_LIB
    NAMES libopenal.so.1 openal
    PATHS ${CMAKE_SOURCE_DIR}/lib
    NO_DEFAULT_PATH
    REQUIRED
)
find_library(CRYPTO_LIB
    NAMES libcrypto.so.1.1 crypto
    PATHS ${CMAKE_SOURCE_DIR}/lib
    NO_DEFAULT_PATH
    REQUIRED
)

# 链接所有库
target_link_libraries(${PROJECT_NAME} PUBLIC
    ${SSL_LIB}
    ${OPENAL_LIB}
    ${CRYPTO_LIB}
    HCCore
    hcnetsdk
    AudioRender
    hpr
    NPQos
    PlayCtrl
    SuperRender
    z
    analyzedata
    AudioIntercom
    HCAlarm
    HCCoreDevCfg
    HCDisplay
    HCGeneralCfgMgr
    HCIndustry
    HCPlayBack
    HCPreview
    HCVoiceTalk
    iconv2
    StreamTransClient
    SystemTransform
    pthread
)

# 确保库文件被复制到正确位置
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:${PROJECT_NAME}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different 
        "${CMAKE_SOURCE_DIR}/lib/libAudioRender.so" 
        $<TARGET_FILE_DIR:${PROJECT_NAME}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different 
        "${CMAKE_SOURCE_DIR}/lib/*.so"
        $<TARGET_FILE_DIR:${PROJECT_NAME}>
    COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:${PROJECT_NAME}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different 
        "${CMAKE_SOURCE_DIR}/lib/HCNetSDKCom/*.so"
        $<TARGET_FILE_DIR:${PROJECT_NAME}>
    COMMENT "Copying required libraries to build directory"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different 
        "${CMAKE_SOURCE_DIR}/*.py"
        $<TARGET_FILE_DIR:${PROJECT_NAME}>
    COMMENT "Copying python files to build directory"
)

#set (Python_ROOT_DIR     "/root/miniconda3/envs/kylin_tobacco_env/bin/python3.10")
#set(pybind11_DIR "/root/miniconda3/envs/kylin_tobacco_env/lib/python3.10/site-packages/pybind11/share/cmake/pybind11")

set (Python_ROOT_DIR     "/home/ubuntu/anaconda3/envs/tobacco_env/bin/python3.10")
set(pybind11_DIR "/home/ubuntu/anaconda3/envs/tobacco_env/lib/python3.10/site-packages/pybind11/share/cmake/pybind11")

#set (Python_ROOT_DIR     "/home/zihui-lang/miniconda3/envs/tobacco_env/bin/python3.10")
#set(pybind11_DIR "/home/zihui-lang/miniconda3/envs/tobacco_env/lib/python3.10/site-packages/pybind11/share/cmake/pybind11")
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

# pybind
pybind11_add_module(camera_api 
    src/pybind_cam_control.cpp
    #src/CamController.cpp
)
# 包含头文件目录
target_include_directories(camera_api PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

# 链接库目录
target_link_directories(camera_api PUBLIC
    ${CMAKE_SOURCE_DIR}/lib
    ${CMAKE_SOURCE_DIR}/lib/HCNetSDKCom
)

target_link_libraries(camera_api PUBLIC
    ${PROJECT_NAME}
    #${SSL_LIB}
    #${OPENAL_LIB}
    #${CRYPTO_LIB}
    #HCCore
    #hcnetsdk
    #AudioRender
    #hpr
    #NPQos
    #PlayCtrl
    #SuperRender
    #z
    #analyzedata
    #AudioIntercom
    #HCAlarm
    #HCCoreDevCfg
    #HCDisplay
    #HCGeneralCfgMgr
    #HCIndustry
    #HCPlayBack
    #HCPreview
    #HCVoiceTalk
    #iconv2
    #StreamTransClient
    #SystemTransform
    #pthread
)
