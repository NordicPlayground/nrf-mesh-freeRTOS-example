set(target "light_switch_freertos_server_${PLATFORM}_${SOFTDEVICE}")

# Common build settings

set(COMMON_COMPILE_OPTIONS
    ${${ARCH}_DEFINES})

set(COMMON_COMPILE_DEFINITIONS
    ${USER_DEFINITIONS}
    -DFREERTOS
    -DAPP_TIMER_IGNORE_FREERTOS
    -DUSE_APP_CONFIG
    -DCONFIG_APP_IN_CORE
    ${${PLATFORM}_DEFINES}
    ${${SOFTDEVICE}_DEFINES}
    ${${BOARD}_DEFINES})


# Remove Mesh memory manager files - the example provides its own
macro (remove_source_files source_files replaced_files)
    set(updated_files ${${source_files}})
    list(REMOVE_ITEM updated_files ${replaced_files})
    set(${source_files} ${updated_files})
endmacro()

set(UPDATED_CORE_SOURCE_FILES ${MESH_CORE_SOURCE_FILES})

if (MESH_MEM_BACKEND STREQUAL "stdlib")
    remove_source_files(
        UPDATED_CORE_SOURCE_FILES
        "${CMAKE_SOURCE_DIR}/mesh/core/src/mesh_mem_stdlib.c")

elseif (MESH_MEM_BACKEND STREQUAL "packet_mgr")
    remove_source_files(
        UPDATED_CORE_SOURCE_FILES
        "${CMAKE_SOURCE_DIR}/mesh/core/src/mesh_mem_packet_mgr.c;${CMAKE_SOURCE_DIR}/mesh/core/src/packet_mgr.c")

elseif (MESH_MEM_BACKEND STREQUAL "mem_manager")
    remove_source_files(
        UPDATED_CORE_SOURCE_FILES
        "${CMAKE_SOURCE_DIR}/mesh/core/src/mesh_mem_mem_manager.c;${SDK_ROOT}/components/libraries/mem_manager/mem_manager.c")
    # TODO: Also remove the include dirs added by this configuration?
    endif()

# FreeRTOS build settings

set(SDK_DRIVER_SOURCE_FILES
    "${SDK_ROOT}/integration/nrfx/legacy/nrf_drv_clock.c"
    "${SDK_ROOT}/modules/nrfx/drivers/src/nrfx_clock.c"
    CACHE INTERNAL "")

set(SDK_DRIVER_INCLUDE_DIRS
    "${SDK_ROOT}/integration/nrfx/legacy"
    "${SDK_ROOT}/modules/nrfx/drivers/include"
    CACHE INTERNAL "")

add_library(freertos
    "${SDK_ROOT}/external/freertos/source/croutine.c"
    "${SDK_ROOT}/external/freertos/source/event_groups.c"
    "${SDK_ROOT}/external/freertos/source/list.c"
    "${SDK_ROOT}/external/freertos/portable/GCC/nrf52/port.c"
    "${SDK_ROOT}/external/freertos/portable/CMSIS/nrf52/port_cmsis.c"
    "${SDK_ROOT}/external/freertos/portable/CMSIS/nrf52/port_cmsis_systick.c"
    "${SDK_ROOT}/external/freertos/source/queue.c"
    "${SDK_ROOT}/external/freertos/source/stream_buffer.c"
    "${SDK_ROOT}/external/freertos/source/tasks.c"
    "${SDK_ROOT}/external/freertos/source/timers.c"
    "${SDK_ROOT}/external/freertos/source/portable/MemMang/heap_4.c"
    ${SDK_DRIVER_SOURCE_FILES})

set(FREERTOS_INCLUDE_DIRS
    "${SDK_ROOT}/external/freertos/config"
    "${SDK_ROOT}/external/freertos/portable/GCC/nrf52"
    "${SDK_ROOT}/external/freertos/portable/CMSIS/nrf52"
    "${SDK_ROOT}/external/freertos/source/include"
    ${SDK_DRIVER_INCLUDE_DIRS}
    CACHE INTERNAL "")

target_include_directories(freertos PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${CMAKE_CURRENT_SOURCE_DIR}/../include"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/mesh_freertos/sdk_modified"
    "${CMAKE_SOURCE_DIR}/examples/common/include"
    ${FREERTOS_INCLUDE_DIRS}
    ${BLE_SOFTDEVICE_SUPPORT_INCLUDE_DIRS}
    ${${SOFTDEVICE}_INCLUDE_DIRS}
    ${${PLATFORM}_INCLUDE_DIRS}
    ${${BOARD}_INCLUDE_DIRS}
    ${${nRF5_SDK_VERSION}_INCLUDE_DIRS})

target_compile_options(freertos PRIVATE
    ${COMMON_COMPILE_OPTIONS})

target_compile_definitions(freertos PRIVATE
    ${COMMON_COMPILE_DEFINITIONS})


# Target build settings

add_executable(${target}
    "${CMAKE_CURRENT_SOURCE_DIR}/src/main.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/mesh_freertos/mesh_mem_freertos.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/mesh_freertos/sdk_modified/nrf_sdh_freertos.c"
    "${CMAKE_SOURCE_DIR}/examples/common/src/app_onoff.c"
    "${CMAKE_SOURCE_DIR}/mesh/stack/src/mesh_stack.c"
    "${CMAKE_SOURCE_DIR}/examples/common/src/mesh_provisionee.c"
    "${MBTLE_SOURCE_DIR}/examples/common/src/rtt_input.c"
    "${CMAKE_SOURCE_DIR}/examples/common/src/simple_hal.c"
    "${CMAKE_SOURCE_DIR}/examples/common/src/mesh_app_utils.c"
    "${CMAKE_SOURCE_DIR}/examples/common/src/app_transition.c"
    ${BLE_SOFTDEVICE_SUPPORT_SOURCE_FILES}
    ${WEAK_SOURCE_FILES}
    ${UPDATED_CORE_SOURCE_FILES}
    ${MESH_BEARER_SOURCE_FILES}
    ${MESH_GATT_SOURCE_FILES}
    ${CONFIG_SERVER_SOURCE_FILES}
    ${HEALTH_SERVER_SOURCE_FILES}
    ${GENERIC_ONOFF_SERVER_SOURCE_FILES}
    ${ACCESS_SOURCE_FILES}
    ${MESH_APP_TIMER_SOURCE_FILES}
    ${PROV_PROVISIONEE_SOURCE_FILES}
    ${PROV_COMMON_SOURCE_FILES}
    ${PROV_BEARER_ADV_SOURCE_FILES}
    ${PROV_BEARER_GATT_SOURCE_FILES}
    ${MESH_FRIEND_SOURCE_FILES}
    ${${PLATFORM}_SOURCE_FILES}
    ${${nRF5_SDK_VERSION}_SOURCE_FILES})

target_include_directories(${target} PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../light_switch/include"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/mesh_freertos/sdk_modified"
    "${CMAKE_SOURCE_DIR}/examples/common/include"
    "${CMAKE_SOURCE_DIR}/external/rtt/include"
    ${BLE_SOFTDEVICE_SUPPORT_INCLUDE_DIRS}
    ${CONFIG_SERVER_INCLUDE_DIRS}
    ${HEALTH_SERVER_INCLUDE_DIRS}
    ${GENERIC_ONOFF_SERVER_INCLUDE_DIRS}
    ${MESH_FRIEND_INCLUDE_DIRS}
    ${MESH_INCLUDE_DIRS}
    ${FREERTOS_INCLUDE_DIRS}
    ${${SOFTDEVICE}_INCLUDE_DIRS}
    ${${PLATFORM}_INCLUDE_DIRS}
    ${${BOARD}_INCLUDE_DIRS}
    ${${nRF5_SDK_VERSION}_INCLUDE_DIRS})

set_target_link_options(${target}
    ${CMAKE_CURRENT_SOURCE_DIR}/linker/${PLATFORM}_${SOFTDEVICE})

target_compile_options(${target} PUBLIC
    ${COMMON_COMPILE_OPTIONS})

target_compile_definitions(${target} PUBLIC
    ${COMMON_COMPILE_DEFINITIONS})

target_link_libraries(${target}
    rtt_${PLATFORM}
    uECC_${PLATFORM}
    freertos)

create_hex(${target})
add_flash_target(${target})

get_property(target_include_dirs TARGET ${target} PROPERTY INCLUDE_DIRECTORIES)
add_pc_lint(${target}
    "${CMAKE_CURRENT_SOURCE_DIR}/src/main.c;${CMAKE_SOURCE_DIR}/examples/common/src/app_onoff.c"
    "${target_include_dirs}"
    "${${PLATFORM}_DEFINES};${${SOFTDEVICE}_DEFINES};${${BOARD}_DEFINES}")
add_ses_project(${target})

if (GENERATE_SES_PROJECTS)
execute_process(
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../patch/patch_ses_project.py "${CMAKE_CURRENT_BINARY_DIR}/${target}.json" "${CMAKE_CURRENT_SOURCE_DIR}"
)
endif (GENERATE_SES_PROJECTS)
