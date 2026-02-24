package com.reskiosk.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalContext
import com.reskiosk.network.HubClient
import kotlinx.coroutines.launch

@Composable
fun HubSetupScreen(onSetupComplete: () -> Unit) {
    val context = LocalContext.current
    val prefs = context.getSharedPreferences("reskiosk_prefs", android.content.Context.MODE_PRIVATE)
    
    var hubUrl by remember { mutableStateOf(prefs.getString("hub_url", "") ?: "") }
    var statusMessage by remember { mutableStateOf("") }
    var keyInfo by remember { mutableStateOf("") }
    var isTesting by remember { mutableStateOf(false) }
    var isSuccess by remember { mutableStateOf(false) }
    
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("Setup Hub Connection", style = MaterialTheme.typography.headlineMedium)
        
        Spacer(modifier = Modifier.height(24.dp))
        
        OutlinedTextField(
            value = hubUrl,
            onValueChange = { hubUrl = it },
            label = { Text("Hub URL (e.g. http://192.168.1.10:8000)") },
            modifier = Modifier.fillMaxWidth()
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Button(onClick = { 
                // Stub for QR Scan
                // In real app, launch scanner, update hubUrl
            }) {
                Text("Scan QR")
            }
            
            Button(
                onClick = {
                    scope.launch {
                        isTesting = true
                        statusMessage = "Testing connection..."
                        isSuccess = false
                        try {
                            val api = HubClient.getApi(context, hubUrl)
                            val ping = api.ping()
                            val netInfo = api.getNetworkInfo()
                            
                            if (ping.status == "ok") {
                                statusMessage = "Connected successfully!"
                                keyInfo = "Hub IP: ${netInfo.hub_ip}\nVersion: ${ping.hub_version}\nKiosks Connected: ${netInfo.connected_kiosks}"
                                isSuccess = true
                                // Save
                                prefs.edit().putString("hub_url", hubUrl).apply()
                            }
                        } catch (e: Exception) {
                            statusMessage = "Connection failed."
                            keyInfo = "Check:\n- Is Hub running?\n- Are you on the same Wi-Fi?\n- Is URL correct?"
                            isSuccess = false
                        } finally {
                            isTesting = false
                        }
                    }
                },
                enabled = hubUrl.startsWith("http") && !isTesting
            ) {
                Text(if (isTesting) "Testing..." else "Test Connection")
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        if (statusMessage.isNotEmpty()) {
            Card(colors = CardDefaults.cardColors(
                containerColor = if (isSuccess) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer
            )) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(statusMessage, style = MaterialTheme.typography.titleMedium)
                    if (keyInfo.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(keyInfo)
                    }
                }
            }
        }
        
        if (isSuccess) {
            Spacer(modifier = Modifier.height(24.dp))
            Button(onClick = onSetupComplete) {
                Text("Continue to Kiosk")
            }
        }
    }
}
