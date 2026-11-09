package com.abolfazl260.flightiranbot24.presentation.tickets

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.data.tickets.HistoryPoint
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.hypot

@Composable
internal fun TicketHistoryDialog(model: TicketHistoryViewModel, onDismiss: () -> Unit, onSupport: () -> Unit) {
    val state by model.state.collectAsState()
    var selected by remember(state) { mutableStateOf<HistoryPoint?>(null) }
    val number = NumberFormat.getNumberInstance(Locale("fa","IR"))
    fun text(p: HistoryPoint) = "${p.day} UTC: ${number.format(p.price)} تومان · ${number.format(p.samples)} ثبت"
    AlertDialog(onDismissRequest=onDismiss, title={ Text("نمودار قیمت ثبت‌شده") },
        confirmButton={TextButton(onClick=onDismiss){Text("بازگشت")}},
        dismissButton={TextButton(onClick=onSupport){Text("رزرو / هماهنگی")}},
        text={Column(Modifier.fillMaxWidth().heightIn(max=520.dp).verticalScroll(rememberScrollState()),
            verticalArrangement=Arrangement.spacedBy(10.dp)) {
            when(val value=state) {
                HistoryUiState.Loading -> Text("در حال دریافت تاریخچه…")
                HistoryUiState.Error -> { Text("دریافت تاریخچه ناموفق بود."); TextButton(onClick=model::retry){Text("تلاش دوباره")} }
                is HistoryUiState.Routes -> {
                    if(value.page.routes.isEmpty())Text("هنوز مسیری دارای تاریخچه نیست.")
                    value.page.routes.forEach { (o,d) -> TextButton(onClick={model.open(o,d)}){Text("از $o به $d")} }
                    if(value.offset>0)TextButton(onClick={model.routes((value.offset-100).coerceAtLeast(0))}){Text("قبلی")}
                    value.page.next?.let { next -> TextButton(onClick={model.routes(next)}){Text("بعدی")} }
                }
                is HistoryUiState.Ready -> {
                    val h=value.history
                    Text("از ${h.origin} به ${h.destination}")
                    Text("کمترین قیمت واقعی هر روز · تومان · ۲۱ روز UTC")
                    Text("${h.start} تا ${h.asOf}")
                    if(h.stale)Text("تاریخچه قدیمی یا فاقد مشاهدهٔ تازه است.",color=MaterialTheme.colorScheme.error)
                    if(h.points.isEmpty())Text("برای این مسیر تاریخچه‌ای ثبت نشده است.") else {
                        fun position(p: HistoryPoint,width: Float,height: Float): Offset {
                            val x=16f+(p.day.toEpochDay()-h.start.toEpochDay()).toFloat()/20f*(width-32f)
                            val spread=(h.maximum!!-h.minimum!!).toDouble()
                            val y=if(spread==0.0)height/2 else height-16f-((p.price-h.minimum!!)/spread*(height-32f)).toFloat()
                            return Offset(x,y)
                        }
                        Canvas(Modifier.fillMaxWidth().height(180.dp).semantics {
                            contentDescription="نمودار قیمت ثبت‌شده؛ مقادیر روزانه در فهرست زیر قابل انتخاب است"
                        }.pointerInput(h) {
                            detectTapGestures { tap -> selected=h.points.minByOrNull { p ->
                                val xy=position(p,size.width.toFloat(),size.height.toFloat())
                                hypot((xy.x-tap.x).toDouble(),(xy.y-tap.y).toDouble())
                            } }
                        }) {
                            h.segments.forEach { (a,b) -> drawLine(Color(0xFF159979),position(a,size.width,size.height),position(b,size.width,size.height),3.dp.toPx()) }
                            h.points.forEach { drawCircle(Color(0xFF159979),5.dp.toPx(),position(it,size.width,size.height)) }
                        }
                        Text("کمینه: ${number.format(h.minimum)} · بیشینه: ${number.format(h.maximum)} تومان")
                        if(h.points.size==1)Text("برای تشخیص روند داده کافی نیست.")
                    }
                    Text("روزهای دارای داده: ${number.format(h.points.size)} از ۲۱ · مشاهدات: ${number.format(h.samples)}")
                    Text("زمان آخرین مشاهده: ${h.observed ?: "ثبت نشده"} UTC")
                    Text(selected?.let(::text) ?: "برای جزئیات، یک نقطه یا ردیف روزانه را لمس کنید.")
                    h.points.forEach { p -> TextButton(onClick={selected=p}){Text(text(p))} }
                    Text("روزهای بدون ثبت خط تخمینی ندارند. قیمت‌ها موجودی قطعی یا رزرو تضمین‌شده نیستند.")
                    TextButton(onClick={model.routes()}){Text("تغییر مسیر")}
                }
            }
        }})
}
