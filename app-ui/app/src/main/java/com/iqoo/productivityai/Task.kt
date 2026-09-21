package com.iqoo.productivityai

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(tableName = "tasks")
data class Task(
    @PrimaryKey
    val id: String = UUID.randomUUID().toString(),
    val title: String = "",
    val type: String = "coding",
    val createdAt: Long = System.currentTimeMillis(),
    val completedAt: Long? = null,
    val duration: Long = 0,
    val location: String = "Home Office",
    val priority: String = "medium"
)