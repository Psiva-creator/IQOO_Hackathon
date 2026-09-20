package com.iqoo.productivity.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

enum class TaskType {
    CODING,
    WRITING,
    MEETING,
    READING,
    PLANNING,
    EXERCISE,
    OTHER
}

enum class Priority {
    LOW,
    MEDIUM,
    HIGH,
    URGENT
}

@Entity(tableName = "tasks")
data class Task(
    @PrimaryKey
    val id: String = UUID.randomUUID().toString(),
    val title: String,
    val type: TaskType,
    val createdAt: Long = System.currentTimeMillis(),
    val completedAt: Long? = null,
    val duration: Long = 0L, // in seconds
    val location: String = "Default",
    val priority: Priority = Priority.MEDIUM
)
