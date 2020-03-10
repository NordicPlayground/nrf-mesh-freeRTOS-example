# FreeRTOS light switch server example

@tag52810nosupport

This example demonstrates how the Mesh stack can coexist with the FreeRTOS library available
in the nRF5 SDK. The Mesh stack takes advantage of FreeRTOS scheduling and task priorities,
so that Mesh can be used more easily in projects and with libraries that use FreeRTOS.
Moreover, the example demonstrates how to resolve hardware and naming conflicts between
the Mesh stack and FreeRTOS.

The example is based on [light switch server example](@ref md_examples_light_switch_server_README),
which was modified to run the low-priority Mesh and BLE stack event processing in FreeRTOS tasks.

In the original light switch server example, much of the logic is executed in an interrupt context,
for example:

- SoftDevice Handler logic is executed in the SWI2 IRQ handler.
- Mesh bearer_event logic is executed in the QDEC IRQ handler.
- Button handling logic (GPIO) is executed in the GPIOTE IRQ handler.
- RTT handling logic is executed in the RTC1 IRQ handler.

In this example, the handler logic for each of these events was moved to FreeRTOS tasks.

**Table of contents**
- [Example breakdown](@ref light_switch_freertos_server_example_breakdown)
- [Hardware requirements](@ref light_switch_freertos_server_example_hw_requirements)
- [Software requirements](@ref light_switch_freertos_server_example_sw_requirements)
- [Setup](@ref light_switch_freertos_server_example_setup)
- [Testing the example](@ref light_switch_freertos_server_example_testing)


Check the documentation pages about [light switch example](@ref md_examples_light_switch_README)
and [light switch server example](@ref md_examples_light_switch_server_README) for the contextual
information needed for running this example.

---

## Example breakdown @anchor light_switch_freertos_server_example_breakdown

To run this example, you must use the modified light switch server example files.

To support FreeRTOS, the following parts of the light switch server example were modified or added:
- [SoftDevice handler logic](@ref light_switch_freertos_server_example_sdh_logic)
- [Mesh bearer_event logic](@ref light_switch_freertos_server_example_bearer_event_logic)
- [Button/RTT handling logic](@ref light_switch_freertos_server_example_button_logic)
- [FreeRTOS initialization](@ref light_switch_freertos_server_example_freertos_init)
- [Memory management](@ref light_switch_freertos_server_example_mem_mgmt)
- [Peripheral conflict handling (RTC usage)](@ref light_switch_freertos_server_example_periph_conflicts)
- [Memory access violation bug fix](@ref light_switch_freertos_server_example_memacc_bugfix)
- [Include order and build output directory](@ref light_switch_freertos_server_example_inc_order)
- [Summary of nRF5 SDK modifications](@ref light_switch_freertos_server_example_sdk_mods)

### SoftDevice handler logic @anchor light_switch_freertos_server_example_sdh_logic

This example contains a modified version of the `nrf_sdh_freertos.c` library from the nRF5 SDK.
This file is used to create a task for handling the SoftDevice Handler events (SDH events)
and executing the handlers in a task.

The stack size assigned to the task in the original file was too small for use with the 
Mesh proxy in the FreeRTOS light switch server example. For this reason, the file was modified
to allow for a configurable stack size.
See [the section on nRF5 SDK modifications](@ref light_switch_freertos_server_example_sdk_mods)
for more information.

The example sets the stack size of this task (`NRF_BLE_FREERTOS_SDH_TASK_STACK`) to `1024`.
The SDH task also requires `NRF_SDH_DISPATCH_MODEL` to be set to `2`
(`NRF_SDH_DISPATCH_MODEL_POLLING`). This setting enables the thread mode processing for
the SoftDevice events.
Both these definitions are set in `app_config.h`.
 
In the example, the `nrf_sdh_freertos` library is initialized in the `initialize()` function
in `main.c`:
```
// Create a FreeRTOS task for handling SoftDevice events.
// That task will call the start function when the task is started.
nrf_sdh_freertos_init(start, &m_device_provisioned);
```

### Mesh bearer_event logic @anchor light_switch_freertos_server_example_bearer_event_logic

The nRF5 SDK for Mesh uses `bearer_event.c` to schedule processing of low priority events
that are non time-critical.

Depending on configuration, the execution can occur either by using the QDEC or SWI0 interrupt,
or in a thread context processing.

For this example, the `bearer_event.c` file was modified to enable the use of both interrupts and
thread context processing.
This enables using the QDEC interrupt to resume a FreeRTOS task that is responsible for the 
actual Mesh processing.

The modified `bearer_event.c` adds the API function `bearer_event_trigger_event_callback_set()`
that allows for registering a callback function.
The callback function is then called to signal the application when the events arrive.

In the example, the callback function is registered in `nrf_mesh_process_thread_init()` in `main.c`:
```
static uint32_t nrf_mesh_process_thread_init(void)
{
    // ...

#if !MESH_FREERTOS_IDLE_HANDLER_RESUME
    bearer_event_trigger_event_callback_set(APP_IRQ_PRIORITY_LOW, mesh_freertos_trigger_event_callback);
#endif

    // ...
}
```
The first parameter passed to `bearer_event_trigger_event_callback_set()` sets the interrupt
priority of the signal, and the second parameter is the callback function. The callback function
`mesh_freertos_trigger_event_callback` resumes the Mesh processing task. See `main.c` for details.

@warning
`bearer_event_trigger_event_callback_set()` must be called **after**
`mesh_stack_init()` has been called with the IRQ priority NRF_MESH_IRQ_PRIORITY_THREAD.
It must also be called before the Mesh stack is started with `mesh_stack_start()`.

The example also supports using the FreeRTOS idle handler to resume the Mesh processing task.
This method is an alternative way to resume the Mesh task that works with an unmodified version of
`bearer_event.c`. The drawback of using the idle handler to resume the Mesh processing task is that
the Mesh task can not preempt other tasks with lower priority than itself and must instead wait for
all other tasks to go idle before resuming. This behaviour could cause stability issues if Mesh is
not able to process events for an extended period of time.

@note
The example resumes the Mesh processing task using the idle handler by default.
It can be switched to resume the task using interrupts by 
setting `MESH_FREERTOS_IDLE_HANDLER_RESUME` to `0` 
in `examples/light_switch_freertos/server/include/nrf_mesh_config_app.h`.

See the functions `nrf_mesh_process_thread_init()` and `mesh_process_thread()` in `main.c` for 
details on how the task is configured and what it does.

The Mesh stack must also be configured to operate in thread processing mode regardless of the method
used to resume the Mesh processing task. In the example, this is done by setting 
`mesh_stack_init_params_t.core.irq_priority` to `NRF_MESH_IRQ_PRIORITY_THREAD` in the call to
 `mesh_stack_init()` in `main.c`.

### Button/RTT handling logic @anchor light_switch_freertos_server_example_button_logic

The button and RTT handling logic in the example both share the same functionality and use the same 
FreeRTOS task. Both the button press and the RTT input result in a call to `button_thread_notify()`,
which notifies the `button_handler_thread()` task (both in `main.c`) of which input was given.
The `button_handler_thread()` function then executes the handler code that handles the input.

### FreeRTOS initialization @anchor light_switch_freertos_server_example_freertos_init

The following snippet is taken from `main.c` and shows the program initialization. Some of the code
from `initialize()` and `start()` has been redacted for simplicity:
```
static void initialize(void)
{
    // ...
    
    // Set up the Mesh processing task for FreeRTOS
    ERROR_CHECK(nrf_mesh_process_thread_init());

    // Set up a task for processing button/RTT events
    if (pdPASS != xTaskCreate(button_handler_thread, "BTN", 512, NULL, 1, &m_button_handler_thread))
    {
        APP_ERROR_HANDLER(NRF_ERROR_NO_MEM);
    }
    
    // Create a FreeRTOS task for handling SoftDevice events.
    // That task will call the start function when the task is started.
    nrf_sdh_freertos_init(start, &m_device_provisioned);
}

static void start(void * p_device_provisioned)
{
    // ... 
    
    ERROR_CHECK(mesh_stack_start());
    
    // ...
}

int main(void)
{
    initialize();

    // Start the FreeRTOS scheduler.
    vTaskStartScheduler();

    for (;;)
    {
        // The app should stay in the FreeRTOS scheduler loop and should never reach this point.
        APP_ERROR_HANDLER(NRF_ERROR_FORBIDDEN);
    }
}
```

The `main()` function first calls `initialize()`, which sets up all the FreeRTOS tasks.

The `start()` function and the `m_device_provisioned` parameter are passed to
`nrf_sdh_freertos_init()` in `initialize()`.
By doing so, the `start()` function is run a single time once the SDH task starts running, and will 
be passed the `m_device_provisioned` parameter. This ensures that `start()` is run in the task 
context.

After the `start()` function, the FreeRTOS scheduler is started with a call to `vTaskStartScheduler()`. 
The scheduler has its own loop and should not return. An assertion will occur if the program
execution ever reaches the bottom loop.

### Memory management @anchor light_switch_freertos_server_example_mem_mgmt

Parts of the Mesh stack require dynamic memory allocation, which is provided to the Mesh in the
@ref MESH_MEM API.

Typically, the `mesh_mem_stdlib.c` implementation is used, which simply
wraps the standard library `malloc()` and `free()`. In this example, `mesh_mem_freertos.c` is
provided to make the memory manager thread-safe and compatible with FreeRTOS. The
`mesh_mem_freertos.c` implementation uses the `pvPortMalloc()` and `vPortFree()` API from FreeRTOS.

The recommended FreeRTOS heap implementation to be used with this library is `heap_4.c`, and that is
what the example uses. The reasons for this are as follows:
* Unlike `heap_1`, `heap_4` has the capability of freeing the allocated memory that is required by the Mesh.
* `heap_4` should have less fragmentation than `heap_2`, which is relevant because the memory allocated
by Mesh is based on message payload length and for this reason can have an arbitrary size.
* Unlike `heap_3`, `heap_4` does not require any actual heap space (it provides its own static buffer),
which makes it simpler to optimize the heap size, and which allows you to allocate the heap from
`FreeRTOSConfig.h`.
* Most applications do not require the additional features offered by `heap_5`.

### Peripheral conflict handling (RTC usage) @anchor light_switch_freertos_server_example_periph_conflicts

The nRF5 SDK for Mesh and FreeRTOS both use RTC1 originally, which leads to a conflict.
This example moves the FreeRTOS implementation to RTC2.

The `xPortSysTickHandler` definition was updated in `FreeRTOSConfig.h`:
`#define xPortSysTickHandler     RTC2_IRQHandler`

The following macros were defined in `app_config.h` to override those set in `portmacro_cmsis.h`:
```
/** Redefine the RTC instance used by FreeRTOS since both Mesh and FreeRTOS use RTC1. */
#ifdef portNRF_RTC_REG
#undef portNRF_RTC_REG
#define portNRF_RTC_REG NRF_RTC2
#endif

/** Redefine the RTC IRQn used by FreeRTOS since both Mesh and FreeRTOS use RTC1 */
#ifdef portNRF_RTC_IRQn
#undef portNRF_RTC_IRQn
#define portNRF_RTC_IRQn RTC2_IRQn
#endif
```

`app_timer.h` from the nRF5 SDK assumes that FreeRTOS uses RTC1.
Therefore, the modified `app_timer.h` included with the example must be used.
See [the section on nRF5 SDK modifications](@ref light_switch_freertos_server_example_sdk_mods).

### Memory access violation bugfix @anchor light_switch_freertos_server_example_memacc_bugfix

The implementation of one of the SoftDevice header files, `nrf_nvic.h`, causes issues with this  
example. When using an unmodified `nrf_nvic.h`, the SoftDevice sometimes triggers a
memory access violation error during the FreeRTOS power management.
See known issues in the SoftDevice s140/s132 v7.0.0 release notes.

This issue can be resolved in several ways:
- By disabling FreeRTOS power management by setting `configUSE_TICKLESS_IDLE` to `0` in
`FreeRTOSConfig.h`.
- By using the modified `nrf_nvic.h` included with this example, located at
`<Path to Mesh SDK>/examples/light_switch_freertos/server/src/mesh_freertos/sdk_modified`

The example by default uses the modified `nrf_nvic.h`, with power management enabled.
See [the section on nRF5 SDK modifications](@ref light_switch_freertos_server_example_sdk_mods)
for more details about the modifications to `nrf_nvic.h`.

### Include order and build output directory @anchor light_switch_freertos_server_example_inc_order  

There are file name conflicts between Mesh and FreeRTOS that must be resolved by the build system.
Additionally, this example contains some modified header files due to assumptions or missing
configuration options in the original header files.

The sensitive directories are the following:
- `<Path to Mesh SDK>/mesh/core/include` contains the Mesh SDK `list.h` and `queue.h`.
- `<Path to nRF5 SDK>/external/freertos/source/include`
    contains the FreeRTOS `list.h` and `queue.h`.
- `<Path to nRF5 SDK>/components/libraries/timer` contains the original `app_timer.h`.
- `<Path to nRF5 SDK>/components/softdevice/<SD version>/headers` contains the original `nrf_nvic.h`.

The first step in order for these conflicts to be resolved is to adhere to the following rules:
- Any Mesh source files should have the directory `<Path to Mesh SDK>/mesh/core/include`
    appear before the directory `<Path to nRF5 SDK>/external/freertos/source/include`.
- Any FreeRTOS source files should have directory 
    `<Path to nRF5 SDK>/external/freertos/source/include` appear before the directory 
    `<Path to Mesh SDK>/mesh/core/include`.
- The order of `<Path to Mesh SDK>/mesh/core/include` and
    `<Path to nRF5 SDK>/external/freertos/source/include` does not matter for the application code, 
    unless it explicitly uses the API defined in these header files.
- Do not include the directory `<Path to nRF5 SDK>/components/libraries/timer`. Instead, use 
    `<Path to Mesh SDK>/examples/light_switch_freertos/server/src/mesh_freertos/sdk_modified`.
- Include the directory `<Path to nRF5 SDK>/components/softdevice/<SD version>/headers`, but
    make sure
    `<Path to Mesh SDK>/examples/light_switch_freertos/server/src/mesh_freertos/sdk_modified`
    appears before it.

In the SEGGER Embedded Studio project for the example, the `<Path to Mesh SDK>/mesh/core/include`
and `<Path to nRF5 SDK>/external/freertos/source/include` are not present in the
global include paths and are instead set individually for each folder.

The second step to resolving the naming conflicts is to specify different output directories for the
object files belonging to Mesh and FreeRTOS. Otherwise, the build may fail as the object
file names for the conflicting files may end up being identical.

In the SEGGER Embedded Studio project for the example, all FreeRTOS object files are placed in
`<build directory>/obj/freertos`.

### Summary of nRF5 SDK modifications @anchor light_switch_freertos_server_example_sdk_mods
The following nRF5 SDK dependencies were modified for the integration to function properly:
- `app_timer.h`
    - **Purpose**: A macro in the original file assumes that FreeRTOS uses the same RTC instance as
      **app\_timer** (if the FREERTOS macro is defined). This behaviour had to be modified so that Mesh
      could use RTC1 properly.
    - **Changes**: Added a way to ignore the FREERTOS macro when calculating APP\_TIMER\_TICKS, by
    defining `APP_TIMER_IGNORE_FREERTOS`:
```
#if !defined(FREERTOS) || defined(APP_TIMER_IGNORE_FREERTOS)
#define APP_TIMER_TICKS(MS)                                \
            ((uint32_t)ROUNDED_DIV(                        \
            (MS) * (uint64_t)APP_TIMER_CLOCK_FREQ,         \
            1000 * (APP_TIMER_CONFIG_RTC_FREQUENCY + 1)))
#else
#include "FreeRTOSConfig.h"
#define APP_TIMER_TICKS(MS) (uint32_t)ROUNDED_DIV((MS)*configTICK_RATE_HZ,1000)
#endif
```
- `nrf_sdh_freertos.c`
    - **Purpose**: The stack size that was originally allocated to the SoftDevice Handler task was too
      small for Mesh operation. As the size was defined by a file local macro, the file had to be updated.  
    - **Changes**: Added a way to define the stack size outside the file, by making the definition
      conditional:
```
#ifndef NRF_BLE_FREERTOS_SDH_TASK_STACK
#define NRF_BLE_FREERTOS_SDH_TASK_STACK 256
#endif
```
- `nrf_nvic.h`
    - **Purpose**: A memory access violation occurs if the MWU
    interrupt is disabled during FreeRTOS power management.
    - **Changes**: Add `MWU_IRQn` to the list of interrupts not disabled by the critical section
    API:
```
#define __NRF_NVIC_SD_IRQS_1 ((uint32_t)(1U << (MWU_IRQn - 32)))
```

@note `nrf_nvic.h` is identical for all the supported SoftDevice versions. Therefore, only one
version of this file is included with the example.

---

## Hardware requirements @anchor light_switch_freertos_server_example_hw_requirements

This example replaces the [light switch servers](@ref md_examples_light_switch_server_README)
in the [light switch example](@ref md_examples_light_switch_README).

It has the same [hardware requirements](@ref light_switch_example_hw_requirements) as the light
switch servers in that example.

---

## Software requirements @anchor light_switch_freertos_server_example_sw_requirements

To test this example, you need the source code of the light switch client example, located
at the following path in the nRF5 SDK for Mesh: `<InstallFolder>/examples/light_switch/client`.

Additional software is required to provision the light switch client and
light switch FreeRTOS servers. This can be done in one of the following alternative ways: 
- By using the [static provisioner](@ref md_examples_light_switch_provisioner_README)
example. The source code for the static provisioner is located at
`<InstallFolder>/examples/light_switch/provisioner`.
- By using the @link_nrf_mesh_app
(available for @link_nrf_mesh_app_ios and @link_nrf_mesh_app_android).

---

## Setup @anchor light_switch_freertos_server_example_setup

You can find the source code of the FreeRTOS light switch server example
in the following nRF5 SDK for Mesh folder: `<InstallFolder>/examples/light_switch_freertos`

### LED and button assignments @anchor light_switch_freertos_server_example_setup_leds_buttons

The LED and button assignments for this example are identical
to the [light switch server example assignments](@ref light_switch_example_setup_leds_buttons).

---

## Testing the example @anchor light_switch_freertos_server_example_testing

To test the FreeRTOS light switch server example, build the examples by following the instructions
in [Building the mesh stack](@ref md_doc_getting_started_how_to_build).

This example replaces the light switch servers. Follow the testing instructions in the
[light switch example documentation](@ref md_examples_light_switch_README).
