import { RoomServiceClient } from 'livekit-server-sdk';
import { NextRequest, NextResponse } from 'next/server';

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

export async function POST(request: NextRequest) {
    if (!API_KEY || !API_SECRET || !LIVEKIT_URL) {
        return new NextResponse('LiveKit credentials not configured', { status: 500 });
    }

    try {
        const body = await request.json();
        const { roomName, identity, allow } = body;

        if (!roomName || !identity || typeof allow !== 'boolean') {
            return new NextResponse('Missing required fields', { status: 400 });
        }

        const roomService = new RoomServiceClient(LIVEKIT_URL, API_KEY, API_SECRET);

        // Update participant permissions
        // We only toggle 'canPublish' for microphone (audio is part of publish).
        // Note: canPublish affects both audio and video usually, unless granular.
        // LiveKit VideoGrant has canPublish, canPublishData.
        // To allow mic but not video is tricky via simple permission if they are bundled.
        // However, the client defaults (students) have video disabled in UI.
        // We just enable publishing generally so they can unmute.

        await roomService.updateParticipant(roomName, identity, undefined, {
            canPublish: allow,
            canSubscribe: true,
            canPublishData: true,
        });

        // If revoking (allow=false), we should also mute the track if it's currently published
        if (!allow) {
            const participant = await roomService.getParticipant(roomName, identity);
            const tracks = participant.tracks;
            for (const track of tracks) {
                if (track.source === 1 || track.source === 2) { // 1=Mic, 2=Camera
                    await roomService.mutePublishedTrack(roomName, identity, track.sid, true);
                }
            }
        }

        return new NextResponse(JSON.stringify({ success: true }), {
            headers: { 'Content-Type': 'application/json' },
        });

    } catch (error) {
        console.error(error);
        return new NextResponse('Failed to update participant', { status: 500 });
    }
}
