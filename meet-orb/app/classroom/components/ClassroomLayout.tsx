'use client';

import React from 'react';
import styles from '../../../styles/ClassroomLayout.module.css';
import {
    useRemoteParticipants,
    useTracks,
    TrackReference,
    VideoTrack,
    ParticipantContext,
    ControlBar,
    useLocalParticipant,
    useRoomContext,
} from '@livekit/components-react';
import { Track, RoomEvent, Participant } from 'livekit-client';
import { ClassroomAudioRenderer } from './ClassroomAudioRenderer';
import { useHandRaising } from '@/lib/useHandRaising';
import { useTranscript } from '@/lib/useTranscript';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'react-hot-toast';

export function ClassroomLayout() {
    const { localParticipant } = useLocalParticipant();
    const isTeacher = localParticipant.metadata?.includes('"role":"teacher"');

    // Find the teacher's video track.
    // For now, we assume the teacher is any participant with 'role' metadata = 'teacher'
    // or simply the first participant who is publishing video if we want to be simpler.
    // In our token policy, only teachers can publish video, so looking for a video track works.

    const videoTracks = useTracks([Track.Source.Camera, Track.Source.ScreenShare]);

    // We expect ideally one teacher video.
    // In the future we might check metadata for role='teacher'.
    const teacherRemoteTrack = videoTracks.find(t => t.participant.metadata?.includes('"role":"teacher"') || t.participant.identity.includes('teacher'));

    // If I am the teacher, show my local track.

    // Construct local track reference manually if teacher
    const localCameraPub = localParticipant.getTrackPublication(Track.Source.Camera);
    const localTrackRef: TrackReference | undefined = localCameraPub ? {
        participant: localParticipant,
        source: Track.Source.Camera,
        publication: localCameraPub
    } : undefined;

    const activeVideoTrack = isTeacher ? localTrackRef : (teacherRemoteTrack ?? videoTracks[0]);

    const { raisedHands, isHandRaised, raiseHand, lowerHand } = useHandRaising();
    const { transcripts } = useTranscript();
    const room = useRoomContext();
    const scrollRef = useRef<HTMLDivElement>(null);
    const [muteTranslation, setMuteTranslation] = useState(false);

    // Auto-scroll to bottom of transcripts
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [transcripts]);

    // Student: Listen for permission changes
    useEffect(() => {
        if (isTeacher || !room) return;
        const handlePermissionsChanged = () => {
            if (room.localParticipant.permissions?.canPublish) {
                toast.success('Teacher has granted you mic access. You can now unmute.');
            } else {
                toast('Mic access revoked.', { icon: '🔒' });
            }
        };
        room.localParticipant.on(RoomEvent.ParticipantPermissionsChanged, handlePermissionsChanged);
        return () => {
            room.localParticipant.off(RoomEvent.ParticipantPermissionsChanged, handlePermissionsChanged);
        };
    }, [room, isTeacher]);

    const handleToggleMic = async (identity: string, currentPermission: boolean) => {
        try {
            await fetch('/api/toggle-mic', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    roomName: room.name,
                    identity,
                    allow: !currentPermission
                })
            });
            toast.success(`Microphone ${!currentPermission ? 'granted' : 'revoked'}`);
        } catch (e) {
            console.error(e);
            toast.error('Failed to toggle mic');
        }
    };

    return (
        <div className={styles.layout}>
            {/* Center Panel: Teacher Video + Transcript */}
            <div className={styles.centerPanel}>
                <div className={styles.teacherVideo}>
                    {activeVideoTrack ? (
                        <ParticipantContext.Provider value={activeVideoTrack.participant}>
                            <VideoTrack trackRef={activeVideoTrack} />
                        </ParticipantContext.Provider>
                    ) : (
                        <div className={styles.placeholderContainer}>
                            <p>Waiting for teacher...</p>
                        </div>
                    )}
                </div>

                <div className={styles.transcriptContainer}>
                    <h3>Live Transcript & Translation</h3>
                    <div className={styles.transcriptList} ref={scrollRef}>
                        {transcripts.length === 0 ? (
                            <p className={styles.subText}>
                                (Waiting for speech...)
                            </p>
                        ) : (
                            transcripts.map((item) => (
                                <div key={item.id} className={styles.transcriptItem}>
                                    <div className={styles.senderName}>{item.senderName || item.senderIdentity}</div>
                                    <div className={`${styles.messageText} ${item.isTranslation ? styles.translationText : ''}`}>
                                        {item.text}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className={styles.controlBarContainer}>
                    <ControlBar controls={{ chat: false, screenShare: false }} />
                    {!isTeacher && (
                        <button
                            className={`lk-button ${styles.raiseHandButton} ${isHandRaised ? styles.activeHandButton : ''}`}
                            onClick={isHandRaised ? lowerHand : raiseHand}
                        >
                            {isHandRaised ? 'Lower Hand' : 'Raise Hand ✋'}
                        </button>
                    )}
                </div>
            </div>

            {/* Audio Renderer must be present for audio to work */}
            <ClassroomAudioRenderer muteTranslation={muteTranslation} />

            {/* Right Sidebar: Participants */}
            <div className={styles.sidebar}>
                <div className={styles.participantsHeader}>
                    <h3>Participants</h3>
                </div>

                <div className={styles.audioToggle}>
                    <input
                        type="checkbox"
                        id="muteTranslation"
                        checked={!muteTranslation}
                        onChange={(e) => setMuteTranslation(!e.target.checked)}
                    />
                    <label htmlFor="muteTranslation">Enable Translation Audio</label>
                </div>

                <CustomParticipantList
                    raisedHands={raisedHands}
                    isTeacher={isTeacher || false}
                    onToggleMic={handleToggleMic}
                />
            </div>
        </div>
    );
}

function CustomParticipantList({
    raisedHands,
    isTeacher,
    onToggleMic
}: {
    raisedHands: Set<string>,
    isTeacher: boolean,
    onToggleMic: (identity: string, currentPermission: boolean) => void
}) {
    const participants = useRemoteParticipants();

    // Sort: Raised hands first, then others
    const sortedParticipants = [...participants].sort((a, b) => {
        const aRaised = raisedHands.has(a.identity);
        const bRaised = raisedHands.has(b.identity);
        if (aRaised && !bRaised) return -1;
        if (!aRaised && bRaised) return 1;
        return 0;
    });

    return (
        <div className={styles.participantList}>
            {sortedParticipants.map((p) => {
                const isPTeacher = p.metadata?.includes('"role":"teacher"');
                const canPublish = p.permissions?.canPublish ?? false;

                return (
                    <div key={p.identity} className={`${styles.participantItem} ${styles.participantRow}`}>
                        <div>
                            {p.name || p.identity}
                            {isPTeacher && (
                                <span className={styles.teacherTag}>Teacher</span>
                            )}
                            {raisedHands.has(p.identity) && (
                                <span className={styles.handIcon}>✋</span>
                            )}
                        </div>
                        {isTeacher && !isPTeacher && (
                            <button
                                className={`lk-button ${styles.micButton}`}
                                onClick={() => onToggleMic(p.identity, canPublish)}
                            >
                                {canPublish ? 'Mute' : 'Allow'}
                            </button>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
