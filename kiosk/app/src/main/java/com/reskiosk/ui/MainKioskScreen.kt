package com.reskiosk.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.Menu
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.reskiosk.viewmodel.KioskState
import com.reskiosk.viewmodel.KioskViewModel
import com.reskiosk.ModelConstants
import com.reskiosk.emergency.EmergencyStrings
import kotlinx.coroutines.launch
import java.io.File

// Page order: 0=Language, 1=Main (default), 2=Hub
private const val PAGE_LANGUAGE = 0
private const val PAGE_MAIN = 1
private const val PAGE_HUB = 2
private const val PAGE_COUNT = 3

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun MainKioskScreen(viewModel: KioskViewModel = viewModel()) {
    val context = LocalContext.current

    // Check for models — if not present, show setup
    val modelsDir = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
    val hasModels = remember {
        File(modelsDir, ModelConstants.STT_DIR_BILINGUAL).exists() &&
        File(modelsDir, ModelConstants.STT_DIR_WHISPER).exists() &&
        File(modelsDir, ModelConstants.TTS_DIR_EN).exists()
    }
    var showSetup by remember { mutableStateOf(!hasModels) }

    // ─── Permission Handling (Aggressive) ───
    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        hasPermission = isGranted
    }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                hasPermission = ContextCompat.checkSelfPermission(
                    context, 
                    Manifest.permission.RECORD_AUDIO
                ) == PackageManager.PERMISSION_GRANTED
                
                if (!hasPermission) {
                    permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    if (showSetup) {
        SetupScreen(onSetupComplete = { showSetup = false })
        return
    }

    if (!hasPermission) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(32.dp)) {
                Icon(Icons.Default.Warning, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.error)
                Spacer(Modifier.height(16.dp))
                Text("Microphone Permission Needed", style = MaterialTheme.typography.headlineMedium, textAlign = TextAlign.Center)
                Spacer(Modifier.height(8.dp))
                Text("Please grant microphone access to use the kiosk.", style = MaterialTheme.typography.bodyLarge, textAlign = TextAlign.Center)
                Spacer(Modifier.height(32.dp))
                Button(onClick = { permissionLauncher.launch(Manifest.permission.RECORD_AUDIO) }) {
                    Text("Grant Permission")
                }
            }
        }
        return
    }

    val pagerState = rememberPagerState(initialPage = PAGE_MAIN, pageCount = { PAGE_COUNT })
    // Hamburger menu Removed -> Re-added as Menu Icon
    var showMenu by remember { mutableStateOf(false) }
    var currentScreen by remember { mutableStateOf(PAGE_MAIN) }

    var showEndSessionDialog by remember { mutableStateOf(false) }

    // ─── Screen Content ───
    Box(modifier = Modifier.fillMaxSize()) {
        when (currentScreen) {
            PAGE_MAIN -> {
                MainPage(
                    viewModel = viewModel, 
                    showEndSessionDialog = showEndSessionDialog,
                    onShowDialogChange = { showEndSessionDialog = it },
                    onNavigateToHub = { currentScreen = PAGE_HUB }
                )
                
                // Top header bar with Menu + Language indicator + End Session
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Left side: Menu Icon and Language Indicator
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        // Menu Icon and Dropdown
                        Box {
                            IconButton(onClick = { showMenu = true }) {
                                Icon(
                                    Icons.Default.Menu, 
                                    contentDescription = "Menu", 
                                    modifier = Modifier.size(32.dp),
                                    tint = MaterialTheme.colorScheme.onSurface 
                                )
                            }
                            
                            DropdownMenu(
                                expanded = showMenu,
                                onDismissRequest = { showMenu = false }
                            ) {
                                DropdownMenuItem(
                                    text = { Text("Language") },
                                    onClick = { 
                                        currentScreen = PAGE_LANGUAGE 
                                        showMenu = false
                                    }
                                )
                                DropdownMenuItem(
                                    text = { Text("Hub Connection") },
                                    onClick = { 
                                        currentScreen = PAGE_HUB 
                                        showMenu = false
                                    }
                                )
                            }
                        }
                        Spacer(Modifier.width(8.dp))
                        val selectedLang by viewModel.selectedLanguage.collectAsState()
                        Text(
                            selectedLang.uppercase(),
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    
                    // End Session Button (Right aligned)
                    val sessionId by viewModel.sessionId.collectAsState()
                    if (sessionId != null) {
                        IconButton(
                            onClick = { showEndSessionDialog = true },
                            modifier = Modifier
                                .border(
                                    width = 1.dp,
                                    color = Color(0xFFE8610A),
                                    shape = CircleShape
                                )
                                .size(32.dp)
                        ) {
                            Icon(
                                Icons.Default.Close,
                                contentDescription = "End Session",
                                modifier = Modifier.size(20.dp), // Matched perfectly with Menu icon layout constraints
                                tint = Color(0xFFE8610A)
                            )
                        }
                    }
                }
            }
            PAGE_LANGUAGE -> {
                LanguageScreen(viewModel = viewModel, onBack = { currentScreen = PAGE_MAIN })
            }
            PAGE_HUB -> {
                HubScreen(viewModel = viewModel, onBack = { currentScreen = PAGE_MAIN })
            }
        }
    }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Main interaction page
// ──────────────────────────────────────────────────────────────────────────────
@Composable
fun MainPage(
    viewModel: KioskViewModel,
    showEndSessionDialog: Boolean,
    onShowDialogChange: (Boolean) -> Unit,
    onNavigateToHub: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val transcript by viewModel.transcript.collectAsState()
    val chatHistory by viewModel.chatHistory.collectAsState()
    val sessionId by viewModel.sessionId.collectAsState()
    val selectedLang by viewModel.selectedLanguage.collectAsState()
    val isListening = uiState is KioskState.Listening
    var showNoHubDialog by remember { mutableStateOf(false) }
    var selectedCategory by remember { mutableStateOf<String?>(null) }

    // Reset selected category when leaving Clarification state
    LaunchedEffect(uiState) {
        if (uiState !is KioskState.Clarification) selectedCategory = null
    }

    // Auto-scroll chat to bottom (including when entering Clarification)
    val listState = rememberLazyListState()
    LaunchedEffect(chatHistory.size, transcript.length, isListening, uiState) {
        val totalItems = chatHistory.size + if (transcript.isNotBlank() && isListening) 1 else 0
        if (totalItems > 0) {
            listState.animateScrollToItem(totalItems - 1)
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        
        if (sessionId == null) {
            // ─── No Session: Welcome + Start Session Button ───
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier.fillMaxSize().padding(horizontal = 32.dp)
            ) {
                Spacer(Modifier.height(80.dp))
                Text(
                    "Welcome to ResKiosk",
                    style = MaterialTheme.typography.displaySmall,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(48.dp))
                Button(
                    onClick = {
                        // Check if hub is connected before starting session
                        if (viewModel.getHubUrl().isBlank()) {
                            showNoHubDialog = true
                        } else {
                            viewModel.startSession()
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth(0.7f)
                        .height(64.dp),
                    shape = RoundedCornerShape(32.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                    elevation = ButtonDefaults.buttonElevation(defaultElevation = 8.dp)
                ) {
                    Text("START SESSION", style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
                }
            }
        } else {
            // ─── Emergency full-screen (manual close only; no auto-dismiss) ───
            when (val s = uiState) {
                is KioskState.EmergencyConfirmation -> {
                    Box(
                        modifier = Modifier.fillMaxSize().background(Color(0xFFB71C1C)),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.padding(48.dp)
                        ) {
                            Text(
                                EmergencyStrings.get("confirm_title", selectedLang),
                                color = Color.White,
                                fontSize = 26.sp,
                                fontWeight = FontWeight.Bold,
                                textAlign = TextAlign.Center
                            )
                            Spacer(Modifier.height(40.dp))
                            Button(
                                onClick = { viewModel.confirmEmergency(s.transcript) },
                                colors = ButtonDefaults.buttonColors(containerColor = Color.White),
                                modifier = Modifier.fillMaxWidth().height(64.dp)
                            ) {
                                Text(
                                    EmergencyStrings.get("confirm_yes", selectedLang),
                                    color = Color(0xFFB71C1C),
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Spacer(Modifier.height(16.dp))
                            OutlinedButton(
                                onClick = { viewModel.cancelEmergency() },
                                border = androidx.compose.foundation.BorderStroke(2.dp, Color.White),
                                modifier = Modifier.fillMaxWidth().height(56.dp)
                            ) {
                                Text(
                                    EmergencyStrings.get("confirm_no", selectedLang),
                                    color = Color.White,
                                    fontSize = 16.sp
                                )
                            }
                        }
                    }
                }
                is KioskState.EmergencyActive -> {
                    val infiniteTransition = rememberInfiniteTransition(label = "sosPulse")
                    val alpha by infiniteTransition.animateFloat(
                        initialValue = 1f,
                        targetValue = 0.3f,
                        animationSpec = infiniteRepeatable(tween(800), RepeatMode.Reverse),
                        label = "alpha"
                    )
                    Box(
                        modifier = Modifier.fillMaxSize().background(Color(0xFFB71C1C)),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.padding(48.dp)
                        ) {
                            Icon(
                                painter = painterResource(com.reskiosk.R.drawable.ic_sos_large),
                                contentDescription = null,
                                tint = Color.White.copy(alpha = alpha),
                                modifier = Modifier.size(80.dp)
                            )
                            Spacer(Modifier.height(24.dp))
                            Text(
                                EmergencyStrings.get("active_title", selectedLang),
                                color = Color.White,
                                fontSize = 30.sp,
                                fontWeight = FontWeight.Bold,
                                textAlign = TextAlign.Center
                            )
                            Spacer(Modifier.height(16.dp))
                            Text(
                                EmergencyStrings.get("active_body", selectedLang),
                                color = Color.White.copy(alpha = 0.9f),
                                fontSize = 18.sp,
                                textAlign = TextAlign.Center
                            )
                            Spacer(Modifier.height(48.dp))
                            TextButton(onClick = { viewModel.dismissEmergency() }) {
                                Text(
                                    EmergencyStrings.get("dismiss", selectedLang),
                                    color = Color.White.copy(alpha = 0.6f),
                                    fontSize = 14.sp
                                )
                            }
                        }
                    }
                }
                is KioskState.TerminatingSession -> {
                    Box(
                        modifier = Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.6f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(0.7f)
                                .background(
                                    Color(0xFF2C2C2C),
                                    RoundedCornerShape(20.dp)
                                )
                                .padding(horizontal = 24.dp, vertical = 28.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(36.dp),
                                    color = Color(0xFFE8610A),
                                    strokeWidth = 3.dp
                                )
                                Spacer(Modifier.height(16.dp))
                                Text(
                                    "Session ending due to inactivity...",
                                    style = MaterialTheme.typography.titleMedium,
                                    color = Color.White,
                                    textAlign = TextAlign.Center
                                )
                            }
                        }
                    }
                }
                else -> {
                    // ─── Active Session: Chat Stream + Record Button ───
                    Box(modifier = Modifier.fillMaxSize()) {
            Box(
                modifier = Modifier.fillMaxSize().padding(top = 56.dp, bottom = 16.dp)
            ) {
                
                // ─── Chat Stream Area (with frame) ───
                Box(
                    modifier = Modifier
                        .fillMaxWidth(0.9f)
                        .fillMaxHeight(0.45f)
                        .padding(top = 8.dp)
                        .align(Alignment.TopCenter)
                        .background(Color(0xFFF9F9F9), RoundedCornerShape(16.dp))
                        .border(1.dp, Color(0xFFE0E0E0), RoundedCornerShape(16.dp))
                        .padding(12.dp)
                ) {
                        if (chatHistory.isEmpty() && transcript.isBlank()) {
                            // Center status indicators on screen when no chat
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                when (val s = uiState) {
                                    is KioskState.Listening -> {
                                        /* Handled by button text change */
                                    }
                                    is KioskState.Error -> {
                                        androidx.compose.animation.AnimatedVisibility(
                                            visible = true,
                                            enter = slideInVertically(initialOffsetY = { it / 2 }) + fadeIn(),
                                            exit = fadeOut()
                                        ) {
                                            Box(
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .background(
                                                        Color(0xFFFFF0E0),
                                                        RoundedCornerShape(12.dp)
                                                    )
                                                    .border(
                                                        1.dp,
                                                        Color(0xFFE8610A).copy(alpha = 0.3f),
                                                        RoundedCornerShape(12.dp)
                                                    )
                                                    .padding(horizontal = 16.dp, vertical = 12.dp),
                                                contentAlignment = Alignment.Center
                                            ) {
                                                Text(
                                                    s.message,
                                                    color = Color(0xFFD32F2F),
                                                    style = MaterialTheme.typography.bodyMedium,
                                                    textAlign = TextAlign.Center
                                                )
                                            }
                                        }
                                    }
                                    is KioskState.Transcribing, is KioskState.Processing -> {
                                        Row(
                                            horizontalArrangement = Arrangement.Center,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                                            Spacer(Modifier.width(8.dp))
                                            Text(
                                                if (uiState is KioskState.Transcribing) "Processing..." else "Asking Hub...",
                                                style = MaterialTheme.typography.titleMedium
                                            )
                                        }
                                    }
                                    is KioskState.Clarification -> {
                                        Column(
                                            horizontalAlignment = Alignment.CenterHorizontally
                                        ) {
                                            Text(s.question, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
                                            Spacer(Modifier.height(8.dp))
                                            s.options.forEach { option ->
                                                Button(
                                                    onClick = {
                                                        selectedCategory = option
                                                        viewModel.selectClarification(option)
                                                    },
                                                    modifier = Modifier.fillMaxWidth(0.6f).padding(vertical = 2.dp),
                                                    enabled = selectedCategory == null
                                                ) {
                                                    if (selectedCategory == option) {
                                                        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                                                            CircularProgressIndicator(
                                                                modifier = Modifier.size(24.dp),
                                                                color = MaterialTheme.colorScheme.onPrimary,
                                                                strokeWidth = 2.dp
                                                            )
                                                        }
                                                    } else {
                                                        Text(option)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    is KioskState.Idle -> {
                                        Text(
                                            "Tap the button below to ask a question",
                                            style = MaterialTheme.typography.bodyLarge,
                                            color = Color.Gray,
                                            textAlign = TextAlign.Center
                                        )
                                    }
                                    else -> { /* Speaking — no text needed */ }
                                }
                            }
                        } else {
                            LazyColumn(
                                state = listState,
                                modifier = Modifier.fillMaxSize(),
                                verticalArrangement = Arrangement.spacedBy(12.dp),
                                contentPadding = PaddingValues(vertical = 8.dp)
                            ) {
                                items(chatHistory) { msg ->
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = if (msg.isUser) Arrangement.End else Arrangement.Start
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .fillMaxWidth(0.8f)
                                                .background(
                                                    if (msg.isUser) Color(0xFFE8E8E8) else Color(0xFFFFF3EC),
                                                    RoundedCornerShape(12.dp)
                                                )
                                                .padding(14.dp)
                                        ) {
                                            Text(
                                                text = msg.text,
                                                style = MaterialTheme.typography.bodyLarge,
                                                color = if (msg.isUser) Color.Black else Color(0xFFE8610A)
                                            )
                                        }
                                    }
                                }
                                
                                // Live Streaming STT Transcript
                                if (transcript.isNotBlank() && uiState is KioskState.Listening) {
                                    item {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.End
                                        ) {
                                            Box(
                                                modifier = Modifier
                                                    .fillMaxWidth(0.8f)
                                                    .background(
                                                        Color(0xFFE8E8E8).copy(alpha = 0.6f),
                                                        RoundedCornerShape(12.dp)
                                                    )
                                                    .padding(14.dp)
                                            ) {
                                                Text(
                                                    text = transcript,
                                                    style = MaterialTheme.typography.bodyLarge,
                                                    color = Color.DarkGray
                                                )
                                            }
                                        }
                                    }
                                }
                                
                                // Clarification Options
                                if (uiState is KioskState.Clarification) {
                                    val s = uiState as KioskState.Clarification
                                    item {
                                        Column(
                                            modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                                            horizontalAlignment = Alignment.CenterHorizontally
                                        ) {
                                            Text(s.question, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center, color = Color(0xFFE8610A))
                                            Spacer(Modifier.height(8.dp))
                                            s.options.forEach { option ->
                                                Button(
                                                    onClick = {
                                                        selectedCategory = option
                                                        viewModel.selectClarification(option)
                                                    },
                                                    modifier = Modifier.fillMaxWidth(0.8f).padding(vertical = 4.dp),
                                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                                                    enabled = selectedCategory == null
                                                ) {
                                                    if (selectedCategory == option) {
                                                        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                                                            CircularProgressIndicator(
                                                                modifier = Modifier.size(24.dp),
                                                                color = Color.White,
                                                                strokeWidth = 2.dp
                                                            )
                                                        }
                                                    } else {
                                                        Text(option, textAlign = TextAlign.Center)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                // ─── Record Button Area (centered in the remaining bottom space) ───
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .fillMaxHeight(0.55f)
                        .align(Alignment.BottomCenter),
                    contentAlignment = Alignment.Center
                ) {
                    Box(
                        contentAlignment = Alignment.Center
                    ) {
                        // Sonar animation — filled concentric circles behind button
                        androidx.compose.animation.AnimatedVisibility(
                            visible = isListening,
                            enter = fadeIn(),
                            exit = fadeOut(animationSpec = tween(600))
                        ) {
                            SonarWave(modifier = Modifier.size(200.dp))
                        }
                        
                        Button(
                            onClick = {
                                if (isListening) {
                                    viewModel.stopListening()
                                } else {
                                    viewModel.startListening()
                                }
                            },
                            modifier = Modifier.size(100.dp),
                            shape = CircleShape,
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                            elevation = ButtonDefaults.buttonElevation(defaultElevation = 6.dp),
                            contentPadding = PaddingValues(4.dp)
                        ) {
                            Text(
                                if (isListening) "Listening..." else "Tap to\nSpeak",
                                style = MaterialTheme.typography.labelMedium,
                                textAlign = TextAlign.Center,
                                color = Color.White
                            )
                        }
                    }
                }
            }

            // ─── Error overlay when chat messages exist ───
            if (chatHistory.isNotEmpty() && uiState is KioskState.Error) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.5f)),
                    contentAlignment = Alignment.Center
                ) {
                    androidx.compose.animation.AnimatedVisibility(
                        visible = true,
                        enter = slideInVertically(initialOffsetY = { it / 2 }) + fadeIn(),
                        exit = fadeOut()
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(0.85f)
                                .background(
                                    Color(0xFFFFF0E0),
                                    RoundedCornerShape(16.dp)
                                )
                                .border(
                                    1.dp,
                                    Color(0xFFE8610A).copy(alpha = 0.3f),
                                    RoundedCornerShape(16.dp)
                                )
                                .padding(horizontal = 20.dp, vertical = 16.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                (uiState as KioskState.Error).message,
                                color = Color(0xFFD32F2F),
                                style = MaterialTheme.typography.bodyMedium,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }
            }

            // ─── SOS FAB (visible except during EmergencyActive) ───
            if (sessionId != null && uiState !is KioskState.EmergencyActive) {
                Box(
                    modifier = Modifier.fillMaxSize().padding(20.dp),
                    contentAlignment = Alignment.BottomStart
                ) {
                    FloatingActionButton(
                        onClick = { viewModel.onSosButtonPressed() },
                        containerColor = Color(0xFFB71C1C),
                        contentColor = Color.White,
                        modifier = Modifier.size(60.dp)
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                painter = painterResource(com.reskiosk.R.drawable.ic_sos),
                                contentDescription = null,
                                modifier = Modifier.size(22.dp)
                            )
                            Text("SOS", fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
                    }
            }
        }
    }
    
    // ─── End Session Confirmation Dialog ───
    if (showEndSessionDialog) {
        AlertDialog(
            onDismissRequest = { onShowDialogChange(false) },
            title = { Text("End Session") },
            text = { Text("This will end your current interaction with ResKiosk and clear the screen.") },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.endSession()
                        onShowDialogChange(false)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD32F2F))
                ) {
                    Text("Confirm")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { onShowDialogChange(false) }) {
                    Text("Back")
                }
            }
        )
    }

    // ─── No Hub Connected Dialog ───
    if (showNoHubDialog) {
        AlertDialog(
            onDismissRequest = { showNoHubDialog = false },
            title = { Text("Kiosk is not connected") },
            text = { Text("Connect to a ResKiosk hub to get started") },
            confirmButton = {
                Button(
                    onClick = {
                        showNoHubDialog = false
                        onNavigateToHub()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
                ) {
                    Text("Connect to Hub")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showNoHubDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Sonar wave animation (filled concentric circles, radiating outward)
// ──────────────────────────────────────────────────────────────────────────────
@Composable
fun SonarWave(modifier: Modifier = Modifier) {
    val primaryColor = Color(0xFFE8610A)
    val transition = rememberInfiniteTransition(label = "sonar")

    // Multiple rings expanding outward, staggered
    val progress1 by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, easing = LinearEasing), RepeatMode.Restart),
        label = "ring1"
    )
    val progress2 by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 400, easing = LinearEasing), RepeatMode.Restart),
        label = "ring2"
    )
    val progress3 by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 800, easing = LinearEasing), RepeatMode.Restart),
        label = "ring3"
    )
    val progress4 by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 1200, easing = LinearEasing), RepeatMode.Restart),
        label = "ring4"
    )
    val progress5 by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 1600, easing = LinearEasing), RepeatMode.Restart),
        label = "ring5"
    )

    Canvas(modifier = modifier) {
        val center = Offset(size.width / 2f, size.height / 2f)
        val maxRadius = size.minDimension / 2f

        listOf(progress1, progress2, progress3, progress4, progress5).forEach { progress ->
            val radius = maxRadius * progress
            val alpha = (1f - progress) * 0.25f
            drawCircle(
                color = primaryColor,
                radius = radius,
                center = center,
                alpha = alpha
            )
        }
    }
}
