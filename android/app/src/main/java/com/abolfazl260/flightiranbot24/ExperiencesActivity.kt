package com.abolfazl260.flightiranbot24

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.data.tickets.*
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.NumberFormat
import java.util.Locale

class ExperiencesActivity: ComponentActivity() {
    override fun attachBaseContext(newBase: Context){super.attachBaseContext(PersianContext.wrap(newBase))}
    override fun onCreate(savedInstanceState: Bundle?){super.onCreate(savedInstanceState)
        setContent {TravelTheme {Surface {Column(Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState())){
            TextButton(onClick=::finish){Text("بازگشت")}
            ExperiencesPanel(intent.getStringExtra("target")?:"",false)
        }}}}
    }
}

@Composable
internal fun ExperiencesPanel(initialTarget: String,compact: Boolean=true){
    val context=LocalContext.current
    val repository=remember(context){ExperiencesRepository(AppContainer(context).publicApi())}
    var target by rememberSaveable(initialTarget){mutableStateOf(initialTarget)}
    var filterKind by rememberSaveable(initialTarget){mutableStateOf(initialTarget.substringBefore(':',"airport"))}
    var search by rememberSaveable(initialTarget){mutableStateOf("")}
    var sort by rememberSaveable(initialTarget){mutableStateOf("newest")}
    var offset by rememberSaveable(initialTarget){mutableIntStateOf(0)}
    var reload by remember{mutableIntStateOf(0)}
    var page by remember(initialTarget){mutableStateOf<ExperiencePage?>(null)}
    var loading by remember{mutableStateOf(true)}
    var error by remember{mutableStateOf(false)}
    LaunchedEffect(target,search,sort,offset,reload){
        loading=true;error=false;page=null
        try {page=withContext(Dispatchers.IO){repository.load(target,search,sort,offset)};if(sort=="rating"&&page?.comparison!=true)sort="newest"}
        catch(e:CancellationException){throw e}
        catch(_:Exception){error=true}
        finally{loading=false}
    }
    val number=NumberFormat.getNumberInstance(Locale("fa","IR"))
    Column(verticalArrangement=Arrangement.spacedBy(10.dp)){
        Text("تجربه‌ها و رضایت مسافران",style=MaterialTheme.typography.titleMedium)
        Text("تجربهٔ شخصی؛ نه مقررات رسمی یا ارزیابی ایمنی پرواز.")
        if(!compact){
            Row(Modifier.horizontalScroll(rememberScrollState())){
                mapOf("airport" to "فرودگاه","airline" to "ایرلاین","country" to "کشور","route" to "مسیر","flight" to "پرواز").forEach{(kind,label)->
                    TextButton(onClick={filterKind=kind;target="";offset=0}){Text((if(filterKind==kind)"✓ "else "")+label)}
                }
            }
            OutlinedTextField(target.substringAfter(':',""),{target=if(it.isBlank())"" else filterKind+":"+it;offset=0},label={Text("کد یا شناسهٔ راهنمای انتخاب‌شده")},modifier=Modifier.fillMaxWidth())
            OutlinedTextField(search,{search=it;offset=0},label={Text("جست‌وجوی متن تجربه")},modifier=Modifier.fillMaxWidth())
            Row {TextButton(onClick={sort="newest";offset=0}){Text((if(sort=="newest")"✓ "else "")+"جدیدترین")}
                TextButton(onClick={sort="helpful";offset=0}){Text((if(sort=="helpful")"✓ "else "")+"مفیدترین")}
                TextButton(onClick={sort="rating";offset=0},enabled=page?.comparison==true){Text((if(sort=="rating")"✓ "else "")+"بالاترین رضایت")}}
        }
        if(loading)Text("در حال دریافت تجربه‌های منتشرشده…")
        if(error)Text("تجربه‌ها فعلاً در دسترس نیستند؛ اتصال یا همگام‌سازی را دوباره بررسی کنید.",color=MaterialTheme.colorScheme.error)
        page?.let { data->
            Text(if(data.count==0)"هنوز رأی رضایت کلیِ تأییدشده‌ای موجود نیست." else
                "رضایت کلی: ${number.format(data.average)} از ۵ · ${number.format(data.count)} رأی"+(if(data.lowSample)" · نمونه کم؛ قابل مقایسه نیست"else ""))
            Text("میانگین سادهٔ رأی‌های منتشرشده؛ هر معیار فقط از رأی همان معیار محاسبه می‌شود. امتیاز کل از ترکیب معیارها ساخته نمی‌شود.")
            data.criteria.forEach { (key,summary) ->
                Text((experienceCriteriaLabels[key]?:key)+": "+number.format(summary.average)+
                    " از ۵ · "+number.format(summary.count)+" رأی"+
                    (if(summary.lowSample)" · نمونه کم" else ""))
            }
            if(data.items.isEmpty())Text("تجربهٔ دارای مجوز و تأیید انتشار برای این فیلتر موجود نیست.")
            data.items.take(if(compact)3 else 10).forEach { row->
                var expanded by rememberSaveable(row.id){mutableStateOf(false)}
                Card(Modifier.fillMaxWidth()){Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(5.dp)){
                    Text(row.name);Text(if(row.kind=="archive")"گزارش آرشیوی با مجوز انتشار"else "تجربهٔ مسافر")
                    Text("تاریخ پیام: ${row.posted?:row.created} · تاریخ سفر: ${row.travelDate?:"مشخص نشده"}")
                    Text(row.rating?.let{"رضایت کلی: ${number.format(it)} از ۵"}?:"بدون رأی عددی")
                    row.criteria.forEach{(key,value)->Text((experienceCriteriaLabels[key]?:key)+": "+number.format(value)+" از ۵")}
                    Text(if(expanded)row.text else row.text.take(160)+(if(row.text.length>160)"…"else ""))
                    TextButton(onClick={expanded=!expanded}){Text(if(expanded)"بستن متن"else "متن کامل")}
                    Text("مفید برای ${number.format(row.helpful)} مسافر")
                    TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(BotLinks.BOT+"?start=xp_review_"+row.id)))}){Text("رأی مفید بودن / گزارش با هویت تلگرام")}
                }}
            }
            if (!compact) {
                Row {
                    if (offset > 0) {
                        TextButton(onClick = { offset = (offset - 10).coerceAtLeast(0) }) {
                            Text("قبلی")
                        }
                    }
                    data.next?.let { next ->
                        TextButton(onClick = { offset = next }) { Text("بعدی") }
                    }
                }
            }
        }
        TextButton(onClick={reload++}){Text("تازه‌سازی")}
        TextButton(onClick={context.startActivity(Intent(context,ExperiencesActivity::class.java).putExtra("target",if(compact)initialTarget else ""))}){Text(if(compact)"همه تجربه‌های این زمینه"else "همه تجربه‌ها")}
        TextButton(onClick={
            val payload=if(target.matches(Regex("(airport:[A-Z]{3}|airline:[a-z0-9-]{2,40}|country:[A-Z]{2}|route:[A-Z]{3}-[A-Z]{3})")))"xp_"+target.replace(":","_") else "experiences"
            context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(BotLinks.BOT+"?start="+payload)))
        }){Text("ثبت / مدیریت تجربه با ورود امن تلگرام")}
    }
}
