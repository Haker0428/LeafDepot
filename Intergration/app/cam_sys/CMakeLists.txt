cmake_minimum_required(VERSION 3.16)
project(cam_sys)

# 设置C++标准
set(CMAKE_CXX_STANDARD 17)

# 添加可执行文件
add_executable(${PROJECT_NAME} 
    src/main.cpp
    src/CameraController.cpp
)

# 包含头文件目录
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_SOURCE_DIR}/include
)

# 链接库目录和具体的库文件
target_link_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_SOURCE_DIR}/lib
    ${CMAKE_SOURCE_DIR}/lib/HCNetSDKCom
)

find_library(OPENAL_LIB
    NAMES libssl.so.1.1
    PATHS ${CMAKE_SOURCE_DIR}/lib
    NO_DEFAULT_PATH  # 不搜索系统路径
)
find_library(SSL_LIB
    NAMES libopenal.so.1
    PATHS ${CMAKE_SOURCE_DIR}/lib
    NO_DEFAULT_PATH  # 不搜索系统路径
)
find_library(CRYPTO_LIB
    NAMES libcrypto.so.1.1
    PATHS ${CMAKE_SOURCE_DIR}/lib
    NO_DEFAULT_PATH  # 不搜索系统路径
)

if(NOT OPENAL_LIB)
    message(FATAL_ERROR "OpenAL library not found in project lib directory")
endif()
if(NOT SSL_LIB)
    message(FATAL_ERROR "SSL library not found in project lib directory")
endif()
if(NOT CRYPTO_LIB)
    message(FATAL_ERROR "CRYPTO library not found in project lib directory")
endif()

# 直接链接.so文件（使用文件名）
target_link_libraries(${PROJECT_NAME} PRIVATE
    ${OPENAL_LIB}   
    ${SSL_LIB} 
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
)