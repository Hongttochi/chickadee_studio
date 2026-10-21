import React, { useEffect, useState } from 'react';
import { RefreshCw, Download, FolderOpen, ArrowUpRight } from 'lucide-react';
import githubIcon from '../assets/github.svg';
const api = window.chickadee;
export default function UpdateSettings() {
  const [state, setState] = useState({ status: 'idle' });
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    const refresh = () => api.updateState().then(value => { if (active) setState(value); }).catch(err => { if (active) setError(err.message); });
    refresh(); const timer = setInterval(refresh, 700);
    return () => { active = false; clearInterval(timer); };
  }, []);
  const busy = ['checking', 'downloading'].includes(state.status);
  async function act(method) { setError(''); try { const next = await api[method](); if (next?.status) setState(next); } catch (err) { setError(err.message); } }
  const message = { idle: 'GitHub 릴리스에서 새 버전을 확인합니다.', checking: '새 버전을 확인하고 있습니다.', current: '현재 버전보다 새로운 릴리스가 없습니다.', available: `${state.version} 버전을 사용할 수 있습니다.`, unsupported: `${state.version} 릴리스에는 이 운영체제·아키텍처용 배포 파일이 없습니다.`, downloading: `다운로드 중 · ${state.progress}%`, downloaded: '파일 검증을 완료했습니다. 앱을 종료한 뒤 ZIP을 새 폴더에 풀어 실행하세요.' }[state.status];
  return <div className="update-settings">
    <div className="update-version"><span>현재 버전</span><strong>{state.current || '—'}</strong>{state.prerelease && <small>새 릴리스 · 사전 공개</small>}</div>
    <div className="update-actions"><button disabled={busy} onClick={() => act('checkUpdates')}><RefreshCw size={15} />업데이트 확인</button>
      <button disabled={state.status !== 'available' || busy} onClick={() => act('downloadUpdate')}><Download size={15} />{state.status === 'downloading' ? '다운로드 중…' : '업데이트 다운로드'}</button>
      {state.status === 'downloaded' && <button onClick={() => act('showUpdateFile')}><FolderOpen size={15} />파일 위치 열기</button>}
    </div>
    {state.status === 'downloading' && <progress aria-label="업데이트 다운로드" value={state.progress} max="100" />}
    <p role="status">{error || state.message || message}</p>
    <button className="update-release-link" onClick={() => act('openReleaseNotes')}><img src={githubIcon} alt="" width="15" height="15" />GitHub 릴리스<ArrowUpRight size={13} /></button>
    <p className="update-note">현재 배포는 ZIP 방식입니다. 다운로드 후 새 버전을 직접 실행하며, 앱이 자동으로 교체되지는 않습니다.</p>
  </div>;
}
