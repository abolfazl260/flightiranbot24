package com.abolfazl260.flightiranbot24

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
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
import android.widget.Toast
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
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
import kotlinx.coroutines.delay

private const val FIDS_LOAD_TIMEOUT_MS = 20_000L
private const val FIDS_BLANK_PAGE_DELAY_MS = 7_000L

// Check for an actually empty rendered document, not merely a page-finished
// callback. JS-heavy sites can finish their initial HTML and still render
// nothing because their scripts or API are unavailable.
private const val FIDS_BLANK_PAGE_SCRIPT = """
(function () {
    var body = document.body;
    if (!body) return true;
    if ((body.innerText || '').trim().length > 0) return false;
    return !body.querySelector('canvas,video,iframe,input,select,button,table');
})()
"""

/**
 * Shows the original official FIDS website inside the app.
 * No first-party FIDS JSON feed is assumed to exist.
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

/** A missing network can be identified without attempting a remote connection. */
private fun hasInternetNetwork(context: Context): Boolean {
    val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
        ?: return true // Unknown connectivity state must not block a valid connection.
    val network = manager.activeNetwork ?: return false
    val capabilities = manager.getNetworkCapabilities(network) ?: return false
    return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
internal fun IranFlightsWebScreen(onClose: () -> Unit) {
    val context = LocalContext.current
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var navigationGeneration by remember { mutableIntStateOf(0) }
    var completedGeneration by remember { mutableIntStateOf(-1) }

    // Keep a single WebView for the lifetime of this screen. Do not silently
    // open other sites, downgrade HTTPS or bypass certificate validation.
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
                        isLoading = false
                        errorMessage = "وب‌سایت رسمی به آدرس دیگری هدایت شد که برای نمایش امن در برنامه مجاز نیست. می‌توانید سایت را در مرورگر بررسی کنید."
                    }
                    return !allowed
                }

                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    if (errorMessage == null) {
                        navigationGeneration++
                        completedGeneration = -1
                        isLoading = true
                    }
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    if (errorMessage == null) {
                        isLoading = false
                        completedGeneration = navigationGeneration
                    }
                }

                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    if (request?.isForMainFrame == true) {
                        isLoading = false
                        errorMessage = when (error?.errorCode) {
                            WebViewClient.ERROR_TIMEOUT -> "زمان اتصال به سامانه اطلاعات پرواز به پایان رسید. اتصال اینترنت یا دسترسی به سایت را بررسی کنید."
                            WebViewClient.ERROR_HOST_LOOKUP -> "آدرس سامانه اطلاعات پرواز پیدا نشد. احتمال اختلال DNS یا محدودیت دسترسی وجود دارد."
                            WebViewClient.ERROR_CONNECT, WebViewClient.ERROR_IO -> "ارتباط با سامانه اطلاعات پرواز برقرار نشد. ممکن است اینترنت یا سرور سایت دچار اختلال باشد."
                            WebViewClient.ERROR_FAILED_SSL_HANDSHAKE -> "اتصال امن به سامانه اطلاعات پرواز برقرار نشد. لطفاً بعداً دوباره تلاش کنید."
                            else -> "بارگذاری سامانه اطلاعات پرواز ناموفق بود. اتصال اینترنت و دسترسی به سایت را بررسی کنید."
                        }
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
                        errorMessage = fidsHttpStatusMessage(errorResponse.statusCode)
                    }
                }

                override fun onReceivedSslError(
                    view: WebView?,
                    handler: SslErrorHandler?,
                    error: SslError?
                ) {
                    handler?.cancel()
                    isLoading = false
                    errorMessage = "گواهی امنیتی سامانه اطلاعات پرواز معتبر نیست. برای امنیت شما صفحه باز نشد."
                }
            }
        }
    }

    DisposableEffect(webView) {
        onDispose {
            webView.stopLoading()
            webView.destroy()
        }
    }

    val retry: () -> Unit = {
        webView.stopLoading()
        errorMessage = null
        completedGeneration = -1
        navigationGeneration++
        if (!hasInternetNetwork(context)) {
            isLoading = false
            errorMessage = "دستگاه به شبکه اینترنت متصل نیست. اینترنت یا وای‌فای را فعال کنید و دوباره تلاش کنید."
        } else {
            isLoading = true
            webView.loadUrl(FIDS_OFFICIAL_HOME)
        }
    }

    // Start only after the WebView has been composed and attached.
    LaunchedEffect(webView) {
        retry()
    }

    // WebView callbacks are not guaranteed if a DNS, proxy, CDN or remote
    // website stalls. Every attempt must have a finite loading state.
    LaunchedEffect(webView, navigationGeneration, isLoading, errorMessage) {
        if (isLoading && errorMessage == null) {
            delay(FIDS_LOAD_TIMEOUT_MS)
            if (isLoading && errorMessage == null) {
                webView.stopLoading()
                isLoading = false
                errorMessage = "پاسخی از سامانه اطلاعات پرواز دریافت نشد. ممکن است سایت موقتاً قطع یا از شبکه شما غیرقابل دسترس باشد."
            }
        }
    }

    // Some sites return HTTP 200 and onPageFinished yet leave an entirely
    // white page. Detect this after a grace period for client-side rendering.
    LaunchedEffect(webView, completedGeneration, isLoading, errorMessage) {
        if (completedGeneration >= 0 && !isLoading && errorMessage == null) {
            val expectedGeneration = completedGeneration
            delay(FIDS_BLANK_PAGE_DELAY_MS)
            if (completedGeneration == expectedGeneration && !isLoading && errorMessage == null) {
                webView.evaluateJavascript(FIDS_BLANK_PAGE_SCRIPT) { isBlank ->
                    if (completedGeneration == expectedGeneration && errorMessage == null &&
                        !isLoading && isBlank == "true"
                    ) {
                        errorMessage = "وب‌سایت باز شد اما اطلاعات پرواز را نمایش نداد. ممکن است بخش‌های داخلی سایت بارگذاری نشده باشند."
                    }
                }
            }
        }
    }

    BackHandler {
        if (errorMessage == null && webView.canGoBack()) webView.goBack() else onClose()
    }

    val openInBrowser: () -> Unit = {
        try {
            context.startActivity(
                Intent(Intent.ACTION_VIEW, Uri.parse(FIDS_OFFICIAL_HOME))
                    .addCategory(Intent.CATEGORY_BROWSABLE)
            )
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(context, R.string.link_unavailable, Toast.LENGTH_LONG).show()
        } catch (_: SecurityException) {
            Toast.makeText(context, R.string.link_unavailable, Toast.LENGTH_LONG).show()
        }
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
                TextButton(onClick = retry) { Text("تازه‌سازی") }
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
                Text(
                    "در حال دریافت اطلاعات از وب‌سایت رسمی فرودگاه‌ها…",
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (errorMessage != null) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        TravelErrorState(
                            message = errorMessage ?: "",
                            onRetry = retry,
                        )
                        TextButton(onClick = openInBrowser) {
                            Text("باز کردن سایت رسمی در مرورگر")
                        }
                        Text(
                            "نمایش ندادن اطلاعات به معنی لغو پروازها نیست. برای پیگیری می‌توانید با اطلاعات پرواز فرودگاه (۱۹۹) تماس بگیرید.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}
