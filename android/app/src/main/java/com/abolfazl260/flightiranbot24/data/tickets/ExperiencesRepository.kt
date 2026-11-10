package com.abolfazl260.flightiranbot24.data.tickets

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import java.net.URLEncoder
import java.time.OffsetDateTime

internal data class PublicExperience(val id: Long,val kind: String,val text: String,val name: String,
    val rating: Int?,val helpful: Int,val targets: List<String>,val created: String,
    val posted: String?,val travelDate: String?,val criteria: Map<String,Int>)
internal val experienceCriteriaLabels = linkedMapOf(
    "crew" to "رفتار خدمه", "seat" to "راحتی صندلی", "catering" to "پذیرایی",
    "cleanliness" to "نظافت", "checkin" to "پذیرش و سوارشدن", "baggage" to "مدیریت بار",
    "value" to "ارزش در برابر هزینه", "delay_response" to "رسیدگی به تأخیر",
    "signage" to "راهنمایی", "queues" to "صف", "services" to "خدمات",
)
internal data class CriterionSummary(val count: Int, val average: Double, val lowSample: Boolean)
internal data class ExperiencePage(val items: List<PublicExperience>,val next: Int?,val count: Int,
    val average: Double?,val lowSample: Boolean,val comparison: Boolean, val criteria: Map<String,CriterionSummary> = emptyMap())
internal class ExperiencesRepository(private val api: PublicJsonRepository<JsonObject>?) {
    suspend fun load(target: String,search: String="",sort: String="newest",offset: Int=0): ExperiencePage {
        fun encode(v:String)=URLEncoder.encode(v,"UTF-8")
        val result=api?.fetch("api/v1/experiences?target=${encode(target)}&q=${encode(search)}&sort=$sort&offset=$offset")
        val raw=when(result){is NetworkResult.Success->result.value;else->error("Experiences unavailable")}
        return parse(raw)?:error("Invalid public experiences")
    }
    fun parse(raw: JsonObject): ExperiencePage?=runCatching {
        val stats=raw.getAsJsonObject("stats");val count=stats.get("rating_count").asInt
        val average=stats.get("average").takeUnless{it.isJsonNull}?.asDouble
        require(count>=0&&(if(count==0)average==null else average!=null&&average.isFinite()&&average in 1.0..5.0))
        require(stats.get("comparison_allowed").asBoolean==(count>=5))
        require(stats.get("low_sample").asBoolean==(count in 1..4))
        val summaries=(stats.getAsJsonObject("criteria")?:JsonObject()).entrySet().associate { (key,v) ->
            require(key in experienceCriteriaLabels)
            val value=v.asJsonObject
            val count=value.get("count").asInt
            val average=value.get("average").asDouble
            val low=value.get("low_sample").asBoolean
            require(value.get("count").asJsonPrimitive.isNumber && value.get("count").asDouble==count.toDouble())
            require(count>0 && average.isFinite() && average in 1.0..5.0 && low==(count<5))
            key to CriterionSummary(count,average,low)
        }
        val values=raw.getAsJsonArray("items");require(values.size()<=10)
        val rows=values.map { item->
            val r=item.asJsonObject;val id=r.get("id").asLong;val kind=r.get("kind").asString
            val text=r.get("text").asString;val name=r.get("display_name").asString
            val rating=r.get("rating").takeUnless{it.isJsonNull}?.asInt
            require(id>0&&kind in listOf("archive","user")&&text.isNotBlank()&&text.length<=20000&&name.length<=80)
            require(rating==null||rating in 1..5);require(kind!="archive"||rating==null)
            val created=r.get("created_at").asString;OffsetDateTime.parse(created)
            require(r.get("helpful").asInt>=0)
            val criteria=(r.getAsJsonObject("criteria")?:JsonObject()).entrySet().associate{it.key to it.value.asInt}
            require(criteria.values.all{it in 1..5})
            PublicExperience(id,kind,text,name,rating,r.get("helpful").asInt,
                r.getAsJsonArray("targets").map{it.asString},created,
                r.get("posted_label")?.takeUnless{it.isJsonNull}?.asString,
                r.get("travel_date")?.takeUnless{it.isJsonNull}?.asString,criteria)
        }
        ExperiencePage(rows,raw.get("next_offset").takeUnless{it.isJsonNull}?.asInt,count,average,
            stats.get("low_sample").asBoolean,count>=5,summaries)
    }.getOrNull()
}
