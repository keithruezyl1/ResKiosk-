package com.reskiosk.stt

import org.junit.Assert.assertEquals
import org.junit.Test

class SttPostProcessorTest {

    @Test fun `phrase correction - registration desk`() {
        assertEquals("Registration desk", SttPostProcessor.process("reg station desk"))
    }

    @Test fun `phrase correction - relief goods`() {
        assertEquals("Relief goods", SttPostProcessor.process("re leaf good"))
    }

    @Test fun `phrase correction - medical station`() {
        assertEquals("Medical station", SttPostProcessor.process("medic all station"))
    }

    @Test fun `word correction - agistration`() {
        assertEquals("Registration", SttPostProcessor.process("agistration"))
    }

    @Test fun `word correction - riskyou`() {
        assertEquals("Rescue", SttPostProcessor.process("riskyou"))
    }

    @Test fun `word correction - evacuation`() {
        assertEquals("Evacuation", SttPostProcessor.process("evakuasyon"))
    }

    @Test fun `word correction - paracetamol`() {
        assertEquals("Paracetamol", SttPostProcessor.process("paresitamol"))
    }

    @Test fun `word correction - volunteer`() {
        assertEquals("Volunteer", SttPostProcessor.process("bolunteer"))
    }

    @Test fun `word correction does not affect correct words`() {
        assertEquals("Registration", SttPostProcessor.process("registration"))
        assertEquals("Medical station", SttPostProcessor.process("medical station"))
        assertEquals("Volunteer", SttPostProcessor.process("volunteer"))
    }

    @Test fun `blank input returns blank`() {
        assertEquals("", SttPostProcessor.process(""))
        assertEquals("", SttPostProcessor.process("   "))
    }

    @Test fun `sentence case applied`() {
        val result = SttPostProcessor.process("where is the food")
        assertEquals('W', result[0])
    }

    @Test fun `phrase corrections applied before word corrections`() {
        // "wrist band" (phrase) should become "wristband", not get partially matched
        assertEquals("Wristband", SttPostProcessor.process("wrist band"))
    }
}
