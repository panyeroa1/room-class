'use client';

import { useTracks, AudioTrack } from '@livekit/components-react';
import { Track } from 'livekit-client';
import React from 'react';
import styles from '../../../styles/ClassroomAudioRenderer.module.css';

export function ClassroomAudioRenderer({ muteTranslation = false }: { muteTranslation?: boolean }) {
    // Subscribe to all microphone audio tracks
    const audioTracks = useTracks([Track.Source.Microphone], { onlySubscribed: true });

    // Filter out teacher tracks
    // Logic: If participant metadata contains "role":"teacher", we skip rendering their audio.
    // This prevents students in the physical room from hearing the teacher through the app (echo).
    // Also filter TTS if muted.
    const filteredTracks = audioTracks.filter((trackRef) => {
        const metadata = trackRef.participant.metadata || '';
        const isTeacher = metadata.includes('"role":"teacher"') || trackRef.participant.identity.includes('teacher');
        const isTTS = metadata.includes('"role":"tts"') || trackRef.participant.identity.includes('tts-bot');

        if (isTeacher) return false;
        if (muteTranslation && isTTS) return false;

        return true;
    });

    return (
        <div className={styles.rendererContainer}>
            {filteredTracks.map((trackRef) => (
                <AudioTrack
                    key={trackRef.publication.trackSid}
                    trackRef={trackRef}
                />
            ))}
        </div>
    );
}
