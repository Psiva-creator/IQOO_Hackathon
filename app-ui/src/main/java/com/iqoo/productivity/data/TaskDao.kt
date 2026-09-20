package com.iqoo.productivity.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.iqoo.productivity.model.Task
import kotlinx.coroutines.flow.Flow

@Dao
interface TaskDao {
    @Query("SELECT * FROM tasks ORDER BY createdAt DESC")
    fun getAllTasks(): Flow<List<Task>>

    @Query("SELECT * FROM tasks WHERE completedAt IS NOT NULL ORDER BY completedAt DESC")
    fun getCompletedTasks(): Flow<List<Task>>

    @Query("SELECT * FROM tasks WHERE completedAt IS NULL ORDER BY createdAt DESC LIMIT 1")
    suspend fun getActiveTask(): Task?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTask(task: Task)

    @Update
    suspend fun updateTask(task: Task)

    @Query("DELETE FROM tasks WHERE id = :taskId")
    suspend fun deleteTask(taskId: String)

    @Query("SELECT * FROM tasks WHERE completedAt IS NOT NULL")
    suspend fun getTasksForAnalytics(): List<Task>
}
