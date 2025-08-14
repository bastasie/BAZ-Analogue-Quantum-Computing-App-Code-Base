/*
 * Example implementation of a D2D computation unit using Android's Wi‑Fi
 * Direct (P2P) API.  This code demonstrates how to discover peers,
 * establish a connection and exchange simple data between devices.  It
 * integrates a very basic version of the BAZ computation: the app
 * computes prime indices and a set of derivative weights which are
 * transmitted to connected peers.  Each device then receives the
 * weights and could apply them to its local RF interface (not
 * implemented here).  The Wi‑Fi Direct APIs are fully supported on
 * Android and allow applications to connect directly to nearby devices
 * without relying on an intermediate access point【694377897110520†L485-L499】.
 *
 * Important notes:
 * - This example does not use 5G NR PC5 sidelink.  5G sidelink
 *   communication is a low‑level radio feature designed for V2X and
 *   mission‑critical applications, and it is not exposed to
 *   application developers on consumer devices.  Instead, Wi‑Fi
 *   Direct provides a practical way to implement device‑to‑device
 *   communication in apps【694377897110520†L485-L499】.
 * - The derivative weights computed here are a placeholder for the
 *   more complex signal processing described in the BAZ EM ladder.
 *   Real deployments would need vendor‑specific APIs to configure RF
 *   beamforming and power control.
 */

package com.example.bazd2d;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.wifi.p2p.WifiP2pConfig;
import android.net.wifi.p2p.WifiP2pDevice;
import android.net.wifi.p2p.WifiP2pDeviceList;
import android.net.wifi.p2p.WifiP2pInfo;
import android.net.wifi.p2p.WifiP2pManager;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity {

    private static final String TAG = "BAZ_D2D";
    private static final int NUM_PRIMES = 8; // number of primes to use
    private static final int SERVER_PORT = 8988;

    private WifiP2pManager manager;
    private WifiP2pManager.Channel channel;
    private BroadcastReceiver receiver;
    private final IntentFilter intentFilter = new IntentFilter();

    private List<WifiP2pDevice> peers = new ArrayList<>();
    private ArrayAdapter<String> peersAdapter;
    private ListView peersListView;
    private Button discoverButton;

    // Whether this device is the group owner (server) or a client
    private boolean isGroupOwner = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Set up the list view and button
        peersListView = findViewById(R.id.peers_list);
        peersAdapter = new ArrayAdapter<>(this,
                android.R.layout.simple_list_item_1, new ArrayList<>());
        peersListView.setAdapter(peersAdapter);
        discoverButton = findViewById(R.id.discover_button);

        // Request necessary permissions (fine location for peer discovery)
        ActivityCompat.requestPermissions(this,
                new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.NEARBY_WIFI_DEVICES,
                        Manifest.permission.ACCESS_WIFI_STATE,
                        Manifest.permission.CHANGE_WIFI_STATE,
                        Manifest.permission.INTERNET},
                1);

        // Initialize Wi‑Fi P2P manager and channel
        manager = (WifiP2pManager) getSystemService(Context.WIFI_P2P_SERVICE);
        if (manager != null) {
            channel = manager.initialize(this, getMainLooper(), null);
        } else {
            Toast.makeText(this, "Wi‑Fi P2P not supported", Toast.LENGTH_LONG).show();
            return;
        }

        // Set up intent filter for Wi‑Fi P2P broadcasts
        intentFilter.addAction(WifiP2pManager.WIFI_P2P_STATE_CHANGED_ACTION);
        intentFilter.addAction(WifiP2pManager.WIFI_P2P_PEERS_CHANGED_ACTION);
        intentFilter.addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION);
        intentFilter.addAction(WifiP2pManager.WIFI_P2P_THIS_DEVICE_CHANGED_ACTION);

        // BroadcastReceiver to handle Wi‑Fi P2P events
        receiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String action = intent.getAction();
                if (WifiP2pManager.WIFI_P2P_STATE_CHANGED_ACTION.equals(action)) {
                    int state = intent.getIntExtra(WifiP2pManager.EXTRA_WIFI_STATE, -1);
                    if (state == WifiP2pManager.WIFI_P2P_STATE_ENABLED) {
                        Toast.makeText(context, "Wi‑Fi Direct is enabled", Toast.LENGTH_SHORT).show();
                    } else {
                        Toast.makeText(context, "Wi‑Fi Direct is disabled", Toast.LENGTH_SHORT).show();
                    }
                } else if (WifiP2pManager.WIFI_P2P_PEERS_CHANGED_ACTION.equals(action)) {
                    // Request peer list
                    if (manager != null) {
                        manager.requestPeers(channel, peerListListener);
                    }
                } else if (WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION.equals(action)) {
                    // Connection state changed
                    if (manager == null) return;
                    manager.requestConnectionInfo(channel, connectionInfoListener);
                }
            }
        };

        // Setup peer list item click to attempt connection
        peersListView.setOnItemClickListener((parent, view, position, id) -> {
            WifiP2pDevice device = peers.get(position);
            WifiP2pConfig config = new WifiP2pConfig();
            config.deviceAddress = device.deviceAddress;
            manager.connect(channel, config, new WifiP2pManager.ActionListener() {
                @Override
                public void onSuccess() {
                    Toast.makeText(MainActivity.this,
                            "Connecting to " + device.deviceName,
                            Toast.LENGTH_SHORT).show();
                }

                @Override
                public void onFailure(int reason) {
                    Toast.makeText(MainActivity.this,
                            "Connection failed: " + reason,
                            Toast.LENGTH_SHORT).show();
                }
            });
        });

        // Discover peers when the button is clicked
        discoverButton.setOnClickListener(v -> discoverPeers());
    }

    @Override
    protected void onResume() {
        super.onResume();
        registerReceiver(receiver, intentFilter);
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(receiver);
    }

    /**
     * Start discovering nearby Wi‑Fi Direct peers.
     */
    private void discoverPeers() {
        manager.discoverPeers(channel, new WifiP2pManager.ActionListener() {
            @Override
            public void onSuccess() {
                Toast.makeText(MainActivity.this, "Discovery initiated", Toast.LENGTH_SHORT).show();
            }

            @Override
            public void onFailure(int reason) {
                Toast.makeText(MainActivity.this,
                        "Discovery failed: " + reason,
                        Toast.LENGTH_SHORT).show();
            }
        });
    }

    /**
     * Listener triggered when the list of peers changes.
     */
    private final WifiP2pManager.PeerListListener peerListListener = new WifiP2pManager.PeerListListener() {
        @Override
        public void onPeersAvailable(WifiP2pDeviceList peerList) {
            peers.clear();
            peers.addAll(peerList.getDeviceList());
            peersAdapter.clear();
            for (WifiP2pDevice device : peers) {
                peersAdapter.add(device.deviceName + "\n" + device.deviceAddress);
            }
            peersAdapter.notifyDataSetChanged();
        }
    };

    /**
     * Listener triggered when connection info is available after a connection
     * is established.
     */
    private final WifiP2pManager.ConnectionInfoListener connectionInfoListener = new WifiP2pManager.ConnectionInfoListener() {
        @Override
        public void onConnectionInfoAvailable(@NonNull WifiP2pInfo info) {
            InetAddress groupOwnerAddress = info.groupOwnerAddress;
            if (info.groupFormed && info.isGroupOwner) {
                // This device is the group owner (server). Start a server to
                // send data to clients.
                isGroupOwner = true;
                new ServerTask().start();
                Toast.makeText(MainActivity.this,
                        "Group Owner: waiting for clients", Toast.LENGTH_SHORT).show();
            } else if (info.groupFormed) {
                // This device is a client. Connect to the group owner and
                // receive data.
                isGroupOwner = false;
                new ClientTask(groupOwnerAddress).start();
                Toast.makeText(MainActivity.this,
                        "Connected as client", Toast.LENGTH_SHORT).show();
            }
        }
    };

    /**
     * Generate the first N prime numbers (skipping 1) to use as indices in
     * the BAZ chain.  This simple sieve returns exactly count primes.
     */
    public static List<Integer> generatePrimeIndices(int count) {
        List<Integer> primes = new ArrayList<>();
        int number = 2;
        while (primes.size() < count) {
            if (isPrime(number)) {
                primes.add(number);
            }
            number++;
        }
        return primes;
    }

    private static boolean isPrime(int n) {
        if (n < 2) return false;
        for (int i = 2; i * i <= n; i++) {
            if (n % i == 0) return false;
        }
        return true;
    }

    /**
     * Compute simple derivative weights for a list of prime indices.  Here we
     * define the derivative as the difference between consecutive primes;
     * the last weight is zero to keep the arrays aligned.
     */
    public static double[] computeDerivativeWeights(List<Integer> primes) {
        double[] weights = new double[primes.size()];
        for (int i = 0; i < primes.size() - 1; i++) {
            weights[i] = primes.get(i + 1) - primes.get(i);
        }
        weights[primes.size() - 1] = 0.0;
        return weights;
    }

    /**
     * Thread that listens for incoming connections and sends the computed
     * weights to each connected client.
     */
    private class ServerTask extends Thread {
        @Override
        public void run() {
            try (ServerSocket serverSocket = new ServerSocket(SERVER_PORT)) {
                // Compute weights once and encode them as a comma‑separated string
                List<Integer> primes = generatePrimeIndices(NUM_PRIMES);
                double[] weights = computeDerivativeWeights(primes);
                StringBuilder payload = new StringBuilder();
                for (int i = 0; i < weights.length; i++) {
                    payload.append(weights[i]);
                    if (i < weights.length - 1) payload.append(",");
                }
                String message = payload.toString();
                Log.d(TAG, "Server prepared weights: " + message);
                while (true) {
                    Socket client = serverSocket.accept();
                    OutputStream out = client.getOutputStream();
                    out.write(message.getBytes());
                    out.close();
                    client.close();
                    Log.d(TAG, "Sent weights to a client");
                }
            } catch (IOException e) {
                Log.e(TAG, "Server error: " + e.getMessage());
            }
        }
    }

    /**
     * Thread that connects to the group owner and receives the weights.
     */
    private class ClientTask extends Thread {
        private final InetAddress hostAddress;
        ClientTask(InetAddress hostAddress) {
            this.hostAddress = hostAddress;
        }

        @Override
        public void run() {
            try (Socket socket = new Socket(hostAddress, SERVER_PORT)) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                String data = reader.readLine();
                reader.close();
                socket.close();
                if (data != null) {
                    Log.d(TAG, "Received weights: " + data);
                    // Parse the weights into a double array
                    String[] parts = data.split(",");
                    double[] weights = new double[parts.length];
                    for (int i = 0; i < parts.length; i++) {
                        try {
                            weights[i] = Double.parseDouble(parts[i]);
                        } catch (NumberFormatException e) {
                            weights[i] = 0.0;
                        }
                    }
                    // In a real implementation, apply weights to the RF
                    // front‑end here.  For demonstration, just log them.
                    for (double w : weights) {
                        Log.d(TAG, "Weight = " + w);
                    }
                }
            } catch (IOException e) {
                Log.e(TAG, "Client error: " + e.getMessage());
            }
        }
    }
}