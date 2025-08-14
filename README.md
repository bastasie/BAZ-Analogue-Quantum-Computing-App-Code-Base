# BAZ-Analogue-Quantum-Computing-App-Code-Base
BAZ D2D Computation Unit

This repository contains a proof‑of‑concept implementation of the BAZ EM ladder computation unit using device‑to‑device (D2D) connectivity. The goal of this project is to demonstrate how a cluster of consumer devices can coordinate and exchange computation weights without relying on a base station or cloud server.

The included Android example leverages Wi‑Fi Direct (P2P) to connect nearby devices and exchange a list of prime‑indexed derivative weights. Wi‑Fi Direct is a standard Android API that allows applications to establish secure, near‑range connections without an intermediate access point. The server (group owner) computes a set of weights derived from the differences between successive prime numbers and pushes them to all connected clients. Clients receive the weights and could, in a real system, apply them to their RF front‑end to realise the BAZ computation. This demo illustrates the basic networking and data‑exchange patterns needed to build a distributed analog computing cluster.

Project Structure

├── android_d2d_example.java   # Android Activity implementing peer discovery, connection and weight exchange
├── baz_em_analog.py           # Reference implementation of the BAZ EM ladder (simulation)
├── baz_d2d_fluid_model.py     # Fluid model for analysing D2D communication (simulation)
├── d2d_computation_simulation.py  # Prior Monte‑Carlo simulation (legacy)
└── README.md                  # This file

The Android example is self‑contained and shows how to:

Request the required runtime permissions (ACCESS_FINE_LOCATION, NEARBY_WIFI_DEVICES, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE and INTERNET).

Discover nearby peers and display them in a simple list.

Establish a P2P group by connecting to a selected device.

Identify the group owner and start a server socket on that device to broadcast data to clients.

Compute a small vector of derivative weights based on the first eight prime numbers and send them to all clients.

Receive and parse the weights on the client side.


In a production system you would extend the weight computation to match the requirements of the BAZ EM ladder and interface with vendor‑specific RF APIs to apply the weights to the hardware. The Wi‑Fi Direct communication layer, however, would remain largely the same.

Building the Example

1. Clone this repository to your local machine.


2. Import the project into Android Studio. The android_d2d_example.java file should be placed inside a package (e.g. com.example.bazd2d) and accompanied by the appropriate layout resources (activity_main.xml with a ListView and a Button).


3. Ensure that your AndroidManifest.xml declares the permissions mentioned above and has minSdkVersion set high enough to support Wi‑Fi Direct (API 14+).


4. Build and run the app on at least two Android devices that support Wi‑Fi Direct. On each device, open the app and tap Discover. After peers appear, select a device on one of the phones to form a group. The group owner will compute and send the weights to the client.



Non‑Commercial License

The source code in this repository is provided under the Creative Commons Attribution‑NonCommercial‑ShareAlike 4.0 International (CC BY‑NC‑SA 4.0) License. This means you are free to share (copy and redistribute the material in any medium or format) and adapt (remix, transform, and build upon the material) for non‑commercial purposes, as long as you:

Give appropriate credit, provide a link to the license and indicate if changes were made.

Distribute your contributions under the same license (share‑alike).

Do not use the material for commercial purposes. Any commercial use—including use in products or services for which payment is received—requires separate written permission from the authors.


Copyright Notice

Copyright © 2025 Oussama Basta 

This work is licensed under the Creative Commons Attribution‑NonCommercial‑ShareAlike 4.0 International License.
To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/.

Disclaimer

This project is an experimental demonstration. It is not a complete implementation of the BAZ EM analog computing chain and does not expose or control any proprietary 5G sidelink features. The authors make no warranties regarding the accuracy, safety or fitness of this software for any particular purpose. Use it at your own risk and only in compliance with the license terms.

