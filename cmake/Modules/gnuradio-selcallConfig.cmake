find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_SELCALL gnuradio-selcall)

FIND_PATH(
    GR_SELCALL_INCLUDE_DIRS
    NAMES gnuradio/selcall/api.h
    HINTS $ENV{SELCALL_DIR}/include
        ${PC_SELCALL_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_SELCALL_LIBRARIES
    NAMES gnuradio-selcall
    HINTS $ENV{SELCALL_DIR}/lib
        ${PC_SELCALL_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-selcallTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_SELCALL DEFAULT_MSG GR_SELCALL_LIBRARIES GR_SELCALL_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_SELCALL_LIBRARIES GR_SELCALL_INCLUDE_DIRS)
