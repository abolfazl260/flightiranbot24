package com.abolfazl260.flightiranbot24

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.net.http.SslError
import android.os.Bundle
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme

/**
 * Displays the original Iranian FIDS website inside the Android application.
 * This is a WebView, NOT the first-party JSON Worker (which has no verified live feed).
 */
class IranFlightsActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TravelTheme {
                IranFlightsWebScreen(onClose = ::finish)
            }
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
internal fun IranFlightsWebScreen(onClose: () -> Unit) {
    val context = LocalContext.current
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var blockedExternalLink by remember { mutableStateOf(false) }

    // Keep one WebView while this screen is composed; retain the site's own
    // airport/direction controls and in-page navigation instead of duplicating them.
    val webView = remember(context) {
        WebView(context).apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                javaScriptCanOpenWindowsAutomatically = false
                setSupportMultipleWindows(false)
                allowFileAccess = false
                allowContentAccess = false
                mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                cacheMode = WebSettings.LOAD_NO_CACHE
            }
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: WebView?,
                    request: WebResourceRequest?
                ): Boolean {
                    val allowed = request?.url?.toString()?.let(::isAllowedFidsNavigation) == true
                    if (!allowed && request?.isForMainFrame == true) {
                        blockedExternalLink = true
                    }
                    // Do not launch Chrome or allow non-HTTPS / unrelated-site navigation.
                    return !allowed
                }

                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    isLoading = true
                    errorMessage = null
                    blockedExternalLink = false
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    isLoading = false
                }

                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    if (request?.isForMainFrame == true) {
                        isLoading = false
                        errorMessage = "اتصال به وب‌سایت رسمی FIDS برقرار نشد. " +
                            "اتصال اینترنت و دسترسی به سایت را بررسی کنید و دوباره تلاش کنید."
                    }
                }

                override fun onReceivedHttpError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    errorResponse: WebResourceResponse?
                ) {
                    if (request?.isForMainFrame == true && errorResponse != null &&
                        errorResponse.statusCode >= 400
                    ) {
                        isLoading = false
                        errorMessage = "وب‌سایت رسمی FIDS خطای " +
                            errorResponse.statusCode + " برگرداند. لطفاً بعداً تلاش کنید."
                    }
                }

                override fun onReceivedSslError(
                    view: WebView?,
                    handler: SslErrorHandler?,
                    error: SslError?
                ) {
                    // Never ignore a certificate error on a flight information site.
                    handler?.cancel()
                    isLoading = false
                    errorMessage = "اتصال امن به وب‌سایت FIDS تأیید نشد. " +
                        "برای حفاظت از اطلاعات، صفحه بارگذاری نشد."
                }
            }
            loadUrl(FIDS_OFFICIAL_HOME)
        }
    }

    DisposableEffect(webView) {
        onDispose {
            webView.stopLoading()
            webView.destroy()
        }
    }

    BackHandler {
        if (webView.canGoBack()) webView.goBack() else onClose()
    }

    val retry: () -> Unit = {
        errorMessage = null
        blockedExternalLink = false
        isLoading = true
        webView.loadUrl(FIDS_OFFICIAL_HOME)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(WindowInsets.safeDrawing),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            TravelToolbar(
                title = stringResource(R.string.iran_fids_title),
                onBack = onClose,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "وب‌سایت رسمی FIDS در داخل برنامه",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                TextButton(onClick = retry) { Text("↻ تازه‌سازی") }
            }
            if (blockedExternalLink) {
                Text(
                    "پیوند خارج از دامنه رسمی FIDS داخل این صفحه باز نمی‌شود.",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }

        Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
            AndroidView(
                factory = { webView },
                modifier = Modifier.fillMaxSize(),
            )

            if (isLoading && errorMessage == null) {
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter),
                )
            }

            if (errorMessage != null) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        TravelErrorState(
                            message = errorMessage ?: "",
                            onRetry = retry,
                        )
                    }
                }
            }
        }
    }
}
