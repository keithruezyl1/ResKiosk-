package com.reskiosk.utils

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.apache.commons.compress.archivers.tar.TarArchiveEntry
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorInputStream
import java.io.BufferedInputStream
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

object ModelDownloader {

    suspend fun downloadAndExtract(
        context: Context, 
        urlString: String, 
        outputDir: File, 
        onProgress: (Float) -> Unit,
        onStatus: (String) -> Unit
    ): Boolean {
        return withContext(Dispatchers.IO) {
            try {
                onStatus("Connecting...")
                var url = URL(urlString)
                var connection = url.openConnection() as HttpURLConnection
                connection.instanceFollowRedirects = false
                connection.connect()

                var responseCode = connection.responseCode
                var maxRedirects = 5
                while ((responseCode == HttpURLConnection.HTTP_MOVED_PERM || 
                        responseCode == HttpURLConnection.HTTP_MOVED_TEMP || 
                        responseCode == HttpURLConnection.HTTP_SEE_OTHER) && maxRedirects > 0) {
                    val redirectUrl = connection.getHeaderField("Location")
                    connection.disconnect()
                    url = URL(redirectUrl)
                    connection = url.openConnection() as HttpURLConnection
                    connection.instanceFollowRedirects = false
                    connection.connect()
                    responseCode = connection.responseCode
                    maxRedirects--
                }

                if (responseCode != HttpURLConnection.HTTP_OK) {
                    Log.e("ModelDownloader", "Server returned HTTP $responseCode for last URL")
                    return@withContext false
                }

                val fileLength = connection.contentLength
                onStatus("Downloading (Size: ${if (fileLength > 0) "${fileLength / 1024 / 1024}MB" else "Unknown"})...")
                val input = BufferedInputStream(connection.inputStream)
                
                // Temp file for download
                val tempFile = File(context.cacheDir, "model_temp.tar.bz2")
                val output = FileOutputStream(tempFile)

                val data = ByteArray(4096)
                var total: Long = 0
                var count: Int
                while (input.read(data).also { count = it } != -1) {
                    total += count.toLong()
                    if (fileLength > 0) {
                        onProgress(total.toFloat() / fileLength)
                    }
                    output.write(data, 0, count)
                }
                output.flush()
                output.close()
                input.close()

                // Extract
                onProgress(1.0f) // Download done
                onStatus("Extracting (this may take a few minutes)...")
                extractTarBz2(tempFile, outputDir)
                tempFile.delete()
                
                true
            } catch (e: Exception) {
                Log.e("ModelDownloader", "Download failed", e)
                false
            }
        }
    }

    private fun extractTarBz2(archive: File, outputDir: File) {
        val fin = archive.inputStream()
        val bin = BufferedInputStream(fin)
        val bzIn = BZip2CompressorInputStream(bin)
        val tarIn = TarArchiveInputStream(bzIn)

        var entry: TarArchiveEntry? = null
        while (tarIn.nextTarEntry.also { entry = it } != null) {
            val outputFile = File(outputDir, entry!!.name)
            if (entry!!.isDirectory) {
                outputFile.mkdirs()
            } else {
                outputFile.parentFile?.mkdirs()
                val fos = FileOutputStream(outputFile)
                val buffer = ByteArray(4096)
                var len: Int
                while (tarIn.read(buffer).also { len = it } != -1) {
                    fos.write(buffer, 0, len)
                }
                fos.close()
            }
        }
        tarIn.close()
        bzIn.close()
        bin.close()
        fin.close()
    }
}
