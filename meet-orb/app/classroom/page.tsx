'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import styles from '../../styles/ClassroomLanding.module.css';

export default function ClassroomLanding() {
    const router = useRouter();
    const [roomName, setRoomName] = useState('classroom-101');

    const join = (role: 'teacher' | 'student') => {
        router.push(`/classroom/${roomName}?role=${role}`);
    };

    return (
        <div className={styles.container}>
            <h1>Classroom Portal</h1>

            <div className={styles.inputGroup}>
                <label htmlFor="roomName">Room Name:</label>
                <input
                    id="roomName"
                    type="text"
                    value={roomName}
                    onChange={(e) => setRoomName(e.target.value)}
                    className={styles.input}
                    placeholder="Enter room name"
                />
            </div>

            <div className={styles.buttonGroup}>
                <button
                    onClick={() => join('teacher')}
                    className={styles.btnTeacher}
                >
                    Create as Teacher
                </button>

                <button
                    onClick={() => join('student')}
                    className={styles.btnStudent}
                >
                    Join as Student
                </button>
            </div>

            <div className={styles.info}>
                <p><strong>Teacher:</strong> Can speak, approve mics, view hand raises.</p>
                <p><strong>Student:</strong> Muted by default, raise hand to speak, hears translation only.</p>
            </div>
        </div>
    );
}
