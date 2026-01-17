/* eslint-disable jsx-a11y/aria-proptypes */
'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import React, { Suspense, useState } from 'react';
import { encodePassphrase, generateRoomId, randomString } from '@/lib/client-utils';
import styles from '../styles/Home.module.css';

function Tabs(props: React.PropsWithChildren<{}>) {
  const searchParams = useSearchParams();
  const tabIndex = searchParams?.get('tab') === 'custom' ? 1 : searchParams?.get('tab') === 'classroom' ? 2 : 0;

  const router = useRouter();
  function onTabSelected(index: number) {
    const tab = index === 1 ? 'custom' : index === 2 ? 'classroom' : 'demo';
    router.push(`/?tab=${tab}`);
  }

  let tabs = React.Children.map(props.children, (child, index) => {
    return (
      <button
        className="lk-button"
        onClick={() => {
          if (onTabSelected) {
            onTabSelected(index);
          }
        }}
        // eslint-disable-next-line react/no-unknown-property
        aria-pressed={tabIndex === index ? 'true' : 'false'}
      >
        {/* @ts-ignore */}
        {child?.props.label}
      </button>
    );
  });

  return (
    <div className={styles.tabContainer}>
      <div className={styles.tabSelect}>{tabs}</div>
      {/* @ts-ignore */}
      {props.children[tabIndex]}
    </div>
  );
}

function DemoMeetingTab(props: { label: string }) {
  const router = useRouter();
  const [e2ee, setE2ee] = useState(false);
  const [sharedPassphrase, setSharedPassphrase] = useState(randomString(64));
  const startMeeting = () => {
    if (e2ee) {
      router.push(`/rooms/${generateRoomId()}#${encodePassphrase(sharedPassphrase)}`);
    } else {
      router.push(`/rooms/${generateRoomId()}`);
    }
  };
  return (
    <div className={styles.tabContent}>
      <p className={styles.description}>Try LiveKit Meet for free with our live demo project.</p>
      <button className={`lk-button ${styles.marginTop}`} onClick={startMeeting}>
        Start Meeting
      </button>
      <div className={styles.flexColumnGap}>
        <div className={styles.flexRowGap}>
          <input
            id="use-e2ee"
            type="checkbox"
            checked={e2ee}
            onChange={(ev) => setE2ee(ev.target.checked)}
          ></input>
          <label htmlFor="use-e2ee">Enable end-to-end encryption</label>
        </div>
        {e2ee && (
          <div className={styles.flexRowGap}>
            <label htmlFor="passphrase">Passphrase</label>
            <input
              id="passphrase"
              type="password"
              value={sharedPassphrase}
              onChange={(ev) => setSharedPassphrase(ev.target.value)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function CustomConnectionTab(props: { label: string }) {
  const router = useRouter();

  const [e2ee, setE2ee] = useState(false);
  const [sharedPassphrase, setSharedPassphrase] = useState(randomString(64));

  const onSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    const formData = new FormData(event.target as HTMLFormElement);
    const serverUrl = formData.get('serverUrl');
    const token = formData.get('token');
    if (e2ee) {
      router.push(
        `/custom/?liveKitUrl=${serverUrl}&token=${token}#${encodePassphrase(sharedPassphrase)}`,
      );
    } else {
      router.push(`/custom/?liveKitUrl=${serverUrl}&token=${token}`);
    }
  };
  return (
    <form className={styles.tabContent} onSubmit={onSubmit}>
      <p className={styles.description}>
        Connect LiveKit Meet with a custom server using LiveKit Cloud or LiveKit Server.
      </p>
      <input
        id="serverUrl"
        name="serverUrl"
        type="url"
        placeholder="LiveKit Server URL: wss://*.livekit.cloud"
        required
      />
      <textarea
        id="token"
        name="token"
        placeholder="Token"
        required
        rows={5}
        className={styles.tokenInput}
      />
      <div className={styles.flexColumnGap}>
        <div className={styles.flexRowGap}>
          <input
            id="use-e2ee"
            type="checkbox"
            checked={e2ee}
            onChange={(ev) => setE2ee(ev.target.checked)}
          ></input>
          <label htmlFor="use-e2ee">Enable end-to-end encryption</label>
        </div>
        {e2ee && (
          <div className={styles.flexRowGap}>
            <label htmlFor="passphrase">Passphrase</label>
            <input
              id="passphrase"
              type="password"
              value={sharedPassphrase}
              onChange={(ev) => setSharedPassphrase(ev.target.value)}
            />
          </div>
        )}
      </div>

      <hr className={styles.separator} />
      <button
        className={`lk-button ${styles.fullWidthButton}`}
        type="submit"
      >
        Connect
      </button>
    </form>
  );
}

function ClassroomTab(props: { label: string }) {
  const router = useRouter();
  const [joinCode, setJoinCode] = useState('');

  const createClassroom = () => {
    const roomId = generateRoomId();
    router.push(`/classroom/${roomId}?role=teacher`);
  };

  const joinClassroom = (e: React.FormEvent) => {
    e.preventDefault();
    if (joinCode) {
      router.push(`/classroom/${joinCode}?role=student`);
    }
  };

  return (
    <div className={styles.tabContent}>
      <p className={styles.description}>Create or Join a Classroom Portal.</p>

      <div className={styles.sectionBorder}>
        <h3>Teacher</h3>
        <button className="lk-button" onClick={createClassroom}>
          Create Classroom
        </button>
      </div>

      <div className={styles.sectionMargin}>
        <h3>Student</h3>
        <form onSubmit={joinClassroom} className={styles.flexColumnGap}>
          <input
            type="text"
            placeholder="Enter Room Code"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            required
          />
          <button className="lk-button" type="submit">
            Join Classroom
          </button>
        </form>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <>
      <main className={styles.main} data-lk-theme="default">
        <div className="header">
          <img src="/images/livekit-meet-home.svg" alt="LiveKit Meet" width="360" height="45" />
          <h2>
            Open source video conferencing app built on{' '}
            <a href="https://github.com/livekit/components-js?ref=meet" rel="noopener">
              LiveKit&nbsp;Components
            </a>
            ,{' '}
            <a href="https://livekit.io/cloud?ref=meet" rel="noopener">
              LiveKit&nbsp;Cloud
            </a>{' '}
            and Next.js.
          </h2>
        </div>
        <Suspense fallback="Loading">
          <Tabs>
            <DemoMeetingTab label="Demo" />
            <CustomConnectionTab label="Custom" />
            <ClassroomTab label="Classroom" />
          </Tabs>
        </Suspense>
      </main>
      <footer data-lk-theme="default">
        Hosted on{' '}
        <a href="https://livekit.io/cloud?ref=meet" rel="noopener">
          LiveKit Cloud
        </a>
        . Source code on{' '}
        <a href="https://github.com/livekit/meet?ref=meet" rel="noopener">
          GitHub
        </a>
        .
      </footer>
    </>
  );
}
