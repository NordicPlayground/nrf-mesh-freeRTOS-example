# FreeRTOS light switch server example

This example project demonstrates how the Mesh stack can coexist with the FreeRTOS library available
in the nRF5 SDK. The Mesh stack takes advantage of FreeRTOS scheduling and task priorities,
so that Mesh can be used more easily in projects and with libraries that use FreeRTOS.
Moreover, the example demonstrates how to resolve hardware and naming conflicts between
the Mesh stack and FreeRTOS.

The example is based on light switch server example from Mesh SDK v4.0.0,
which was modified to run the low-priority Mesh and BLE stack event processing in FreeRTOS tasks.

---

## Software requirements
This example requires the following additional software:
- [Mesh SDK v4.0.0](https://www.nordicsemi.com/Software-and-tools/Software/nRF5-SDK-for-Mesh/Download#infotabs)
- [nRF5 SDK v16.0.0](https://www.nordicsemi.com/Software-and-tools/Software/nRF5-SDK/Download#infotabs)

---

## Setup

### Windows
To set up the example, copy the `examples` and `mesh` directories from the root directory of this
repository into the root directory of Mesh SDK v4.0.0.
This should result in some files from Mesh SDK being replaced by files from this repository.

### Other platforms
To set up the example, the contents of the `examples` and `mesh` directories from the root
directory of this repository should be merged into the corresponding `examples` and `mesh`
directories in the root directory of Mesh SDK v4.0.0. It is important that the existing file
hierarchy in Mesh SDK is preserved - only the files replaced by this project should be modified.
Please follow instructions specific to your platform on how to merge these directories.

---

## Testing the example
To build and test the example, follow the
[instructions in the example documentation](examples/light_switch_freertos/server/README.md).
