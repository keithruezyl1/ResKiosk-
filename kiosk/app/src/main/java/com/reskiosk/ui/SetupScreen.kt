package com.reskiosk.ui

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.reskiosk.utils.ModelDownloader
import kotlinx.coroutines.launch
import com.reskiosk.ModelConstants
import androidx.compose.ui.text.font.FontWeight
import android.util.Log
import java.io.File

@Composable
fun SetupScreen(onSetupComplete: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    // Paths (from ModelConstants — single source of truth)
    val modelsDir = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
    val requiredDirs = listOf(
        "English STT" to File(modelsDir, ModelConstants.STT_DIR_BILINGUAL),
        "Whisper STT" to File(modelsDir, ModelConstants.STT_DIR_WHISPER),
        "English Voice" to File(modelsDir, ModelConstants.TTS_DIR_EN),
        "Spanish Voice" to File(modelsDir, ModelConstants.TTS_DIR_ES),

        "Punctuation" to File(modelsDir, ModelConstants.PUNCTUATION_DIR)
    )
    
    var modelsExist by remember { mutableStateOf(requiredDirs.all { (_, dir) -> dir.exists() && (dir.list()?.isNotEmpty() ?: false) }) }
    var downloadProgress by remember { mutableStateOf(0f) }
    var isDownloading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("Welcome to ResKiosk") }
    
    val downloads = listOf(
        "English STT" to ModelConstants.STT_URL_BILINGUAL,
        "Whisper STT" to ModelConstants.STT_URL_WHISPER,
        "English Voice" to ModelConstants.TTS_URL_EN,
        "Spanish Voice" to ModelConstants.TTS_URL_ES,

        "Punctuation" to ModelConstants.PUNCTUATION_URL
    )

    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
    ) {
        // Header
        Text(
            "Setup",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(start = 8.dp, top = 16.dp)
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Column(
            modifier = Modifier.fillMaxWidth().weight(1f).padding(horizontal = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
        Text("ResKiosk Setup", style = MaterialTheme.typography.headlineLarge)
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(message, textAlign = TextAlign.Center)
        Spacer(modifier = Modifier.height(24.dp))
        
        if (isDownloading) {
            LinearProgressIndicator(progress = downloadProgress, modifier = Modifier.fillMaxWidth())
            Spacer(modifier = Modifier.height(8.dp))
            Text("${(downloadProgress * 100).toInt()}%")
        } else if (!modelsExist) {
            Button(onClick = {
                isDownloading = true
                scope.launch {
                    var allSuccess = true
                    for ((index, item) in downloads.withIndex()) {
                        val (name, url) = item
                        val targetDir = requiredDirs.find { it.first == name }?.second
                        
                        // Incremental check: Skip if directory exists and is not empty
                        if (targetDir != null && targetDir.exists() && (targetDir.list()?.isNotEmpty() ?: false)) {
                            Log.i("SetupScreen", "Skipping $name, already installed.")
                            downloadProgress = (index + 1).toFloat() / downloads.size
                            continue
                        }

                        message = "Setting up $name (${index + 1}/${downloads.size})..."
                        val success = ModelDownloader.downloadAndExtract(
                            context = context,
                            urlString = url,
                            outputDir = modelsDir,
                            onProgress = { prog ->
                                downloadProgress = (index.toFloat() / downloads.size) + (prog / downloads.size)
                            },
                            onStatus = { status ->
                                message = "$name: $status"
                            }
                        )
                        if (!success) {
                            message = "$name Download Failed. Check Internet."
                            allSuccess = false
                            break
                        }
                    }
                    if (allSuccess) {
                        message = "Models Ready!"
                        modelsExist = true
                    }
                    isDownloading = false
                }
            }) {
                Text(if (requiredDirs.any { (_, dir) -> dir.exists() }) "Resume Setup" else "Download Offline Models")
            }
        }
 else {
            // Models exist. Verification step.
             Button(onClick = onSetupComplete) {
                Text("Start Kiosk")
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text("Models Found.", style = MaterialTheme.typography.bodySmall)
            Spacer(modifier = Modifier.height(16.dp))
            OutlinedButton(onClick = {
                // Delete existing models and re-download
                requiredDirs.forEach { it.second.deleteRecursively() }
                modelsExist = false
                message = "Old models cleared. Tap Download to get fresh models."
            }) {
                Text("Re-download Models")
            }
        }
        }
    }
}
