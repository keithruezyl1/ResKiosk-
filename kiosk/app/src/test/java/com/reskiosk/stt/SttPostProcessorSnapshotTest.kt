package com.reskiosk.stt

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Regression snapshot tests: known noisy inputs must produce expected normalized output.
 * When modifying the SttPostProcessor pipeline, ensure these cases still pass.
 */
class SttPostProcessorSnapshotTest {

    @Test fun `snapshot - uh where where is the the food`() {
        assertEquals("Where is the food", SttPostProcessor.process("uh where where is the the food"))
    }

    @Test fun `snapshot - um i need agistration help`() {
        assertEquals("I need registration help", SttPostProcessor.process("um i need agistration help"))
    }

    @Test fun `snapshot - medic all station where`() {
        assertEquals("Medical station where", SttPostProcessor.process("medic all station where"))
    }

    @Test fun `snapshot - i am i am hungry um`() {
        assertEquals("I am hungry", SttPostProcessor.process("i am i am hungry um"))
    }

    @Test fun `snapshot - seven am breakfast where where`() {
        assertEquals("7 am breakfast where", SttPostProcessor.process("seven am breakfast where where"))
    }

    @Test fun `snapshot - re leaf goods distribution when`() {
        assertEquals("Relief goods distribution when", SttPostProcessor.process("re leaf goods distribution when"))
    }

    @Test fun `snapshot - wrist band lost i lost my wrist van`() {
        assertEquals("Wristband lost i lost my wristband", SttPostProcessor.process("wrist band lost i lost my wrist van"))
    }
}
