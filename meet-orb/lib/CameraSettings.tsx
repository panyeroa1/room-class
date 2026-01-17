import React from 'react';
import {
  MediaDeviceMenu,
  TrackReference,
  TrackToggle,
  useLocalParticipant,
  VideoTrack,
} from '@livekit/components-react';
import { BackgroundBlur, VirtualBackground } from '@livekit/track-processors';
import { isLocalTrack, LocalTrackPublication, Track } from 'livekit-client';
import styles from '../styles/CameraSettings.module.css';

// Background image paths
const BACKGROUND_IMAGES: { name: string; path: any }[] = [];

// Background options
type BackgroundType = 'none' | 'blur' | 'image';

export function CameraSettings() {
  const { cameraTrack, localParticipant } = useLocalParticipant();
  const [backgroundType, setBackgroundType] = React.useState<BackgroundType>(
    (cameraTrack as LocalTrackPublication)?.track?.getProcessor()?.name === 'background-blur'
      ? 'blur'
      : (cameraTrack as LocalTrackPublication)?.track?.getProcessor()?.name === 'virtual-background'
        ? 'image'
        : 'none',
  );

  const [virtualBackgroundImagePath, setVirtualBackgroundImagePath] = React.useState<string | null>(
    null,
  );

  const camTrackRef: TrackReference | undefined = React.useMemo(() => {
    return cameraTrack
      ? { participant: localParticipant, publication: cameraTrack, source: Track.Source.Camera }
      : undefined;
  }, [localParticipant, cameraTrack]);

  const selectBackground = (type: BackgroundType, imagePath?: string) => {
    setBackgroundType(type);
    if (type === 'image' && imagePath) {
      setVirtualBackgroundImagePath(imagePath);
    } else if (type !== 'image') {
      setVirtualBackgroundImagePath(null);
    }
  };

  React.useEffect(() => {
    if (isLocalTrack(cameraTrack?.track)) {
      if (backgroundType === 'blur') {
        cameraTrack.track?.setProcessor(BackgroundBlur());
      } else if (backgroundType === 'image' && virtualBackgroundImagePath) {
        cameraTrack.track?.setProcessor(VirtualBackground(virtualBackgroundImagePath));
      } else {
        cameraTrack.track?.stopProcessor();
      }
    }
  }, [cameraTrack, backgroundType, virtualBackgroundImagePath]);

  return (
    <div className={styles.container}>
      {camTrackRef && <VideoTrack className={styles.videoTrack} trackRef={camTrackRef} />}

      <section className="lk-button-group">
        <TrackToggle source={Track.Source.Camera}>Camera</TrackToggle>
        <div className="lk-button-group-menu">
          <MediaDeviceMenu kind="videoinput" />
        </div>
      </section>

      <div className={styles.backgroundEffectsContainer}>
        <div className={styles.backgroundEffectsLabel}>Background Effects</div>
        <div className={styles.backgroundOptions}>
          <button
            onClick={() => selectBackground('none')}
            className={`lk-button ${styles.optionButton} ${backgroundType === 'none' ? styles.optionButtonActive : ''
              }`}
            // eslint-disable-next-line react/no-unknown-property
            aria-pressed={backgroundType === 'none' ? 'true' : 'false'}
          >
            None
          </button>

          <button
            onClick={() => selectBackground('blur')}
            className={`lk-button ${styles.optionButton} ${styles.blurButton} ${backgroundType === 'blur' ? styles.optionButtonActive : ''
              }`}
            // eslint-disable-next-line react/no-unknown-property
            aria-pressed={backgroundType === 'blur' ? 'true' : 'false'}
          >
            <div className={styles.blurPreview} />
            <span className={styles.blurLabel}>Blur</span>
          </button>

          {BACKGROUND_IMAGES.map((image) => (
            <button
              key={image.path.src}
              onClick={() => selectBackground('image', image.path.src)}
              className={`lk-button ${styles.optionButton} ${styles.imageButton} ${backgroundType === 'image' && virtualBackgroundImagePath === image.path.src
                ? styles.optionButtonActive
                : ''
                }`}
              // eslint-disable-next-line react/no-unknown-property
              aria-pressed={backgroundType === 'image' && virtualBackgroundImagePath === image.path.src ? 'true' : 'false'}
              // eslint-disable-next-line react/forbid-dom-props
              style={{
                // @ts-ignore
                '--bg-image': `url(${image.path.src})`,
              }}
            >
              <span className={styles.imageLabel}>{image.name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
