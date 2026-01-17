'use client';

import React, { ReactNode } from 'react';
import styles from '../../../styles/ClassroomShell.module.css';

interface ClassroomShellProps {
    children: ReactNode;
    roomName: string;
}

export function ClassroomShell({ children, roomName }: ClassroomShellProps) {
    return (
        <div className={styles.shell}>
            <header className={styles.header}>
                <h3>Classroom Mode: {roomName}</h3>
            </header>
            <div className={styles.content}>
                {children}
            </div>
        </div>
    );
}
