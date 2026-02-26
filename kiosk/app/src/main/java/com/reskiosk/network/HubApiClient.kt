package com.reskiosk.network

import com.google.gson.annotations.SerializedName
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

// --- Response model ---

data class HubQueryResponse(
    @SerializedName("answer_text_en") val answerTextEn: String?,
    @SerializedName("answer_text_localized") val answerTextLocalized: String?,
    @SerializedName("answer_type") val answerType: String?,
    @SerializedName("clarification_categories") val clarificationCategories: List<String>?,
    @SerializedName("source_id") val sourceId: Int?,
    @SerializedName("query_log_id") val queryLogId: Int?,
    @SerializedName("rlhf_top_source_id") val rlhfTopSourceId: Int?,
    @SerializedName("rlhf_top_score") val rlhfTopScore: Float?
)

data class PingResponse(
    val status: String?,
    @SerializedName("hub_version") val hubVersion: String?
)

// --- Retrofit interface ---

interface HubApiService {
    @POST("query")
    suspend fun query(@Body payload: Map<String, @JvmSuppressWildcards Any?>): HubQueryResponse

    @POST("feedback")
    suspend fun feedback(@Body payload: Map<String, @JvmSuppressWildcards Any?>): Any

    @GET("admin/ping")
    suspend fun ping(): PingResponse

    @POST("register_kiosk")
    suspend fun heartbeat(@Body payload: Map<String, String>): Any

    @POST("emergency")
    suspend fun emergency(@Body payload: Map<String, @JvmSuppressWildcards Any?>): Any

    @retrofit2.http.DELETE("query/session/{session_id}")
    suspend fun endSession(@retrofit2.http.Path("session_id") sessionId: String): Any
}

// --- Singleton client ---

object HubApiClient {
    private var cachedUrl: String? = null
    private var service: HubApiService? = null
    private var kioskId: String = "kiosk_1"

    fun setKioskId(id: String) {
        kioskId = id
    }

    fun getService(baseUrl: String): HubApiService {
        val normalizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        // Rebuild if URL changed or not yet created
        if (normalizedUrl != cachedUrl || service == null) {
            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(120, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .addInterceptor(Interceptor { chain ->
                    val request = chain.request().newBuilder()
                        .addHeader("X-Kiosk-ID", kioskId)
                        .build()
                    chain.proceed(request)
                })
                .build()

            service = Retrofit.Builder()
                .baseUrl(normalizedUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(HubApiService::class.java)
            cachedUrl = normalizedUrl
        }
        return service!!
    }
}
