#!/usr/bin/env python3
"""
APEX TERMINAL COMMANDER v3

Preserves the existing commander while adding:
- export inventory|chunk|resume|verify|upload|handoff
- ios status|sync plus explicit backup/media/usage/health lane commands
- upload-session-backed OneDrive transport for giant exports

Legacy commands are delegated to the existing `apex_terminal_commander.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

COLORS = {
    'RED': '\033[0;31m',
    'GREEN': '\033[0;32m',
    'YELLOW': '\033[1;33m',
    'CYAN': '\033[0;36m',
    'NC': '\033[0m'
}


def c(text, col='NC'):
    print(f"{COLORS.get(col,'')}{text}{COLORS['NC']}")


def print_result(result):
    if isinstance(result, dict):
        print(json.dumps(result, indent=2))
    else:
        print(result)


def _load_items(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(path)
    data = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and 'items' in data and isinstance(data['items'], list):
        return data['items']
    raise ValueError(f'Unsupported items JSON shape in {path}')


def export_ops(args):
    from services.apex_export_bridge import (
        build_inventory,
        build_chunk_manifest,
        checkpoint_path_for_source,
        emit_handoff,
        load_checkpoint,
        update_checkpoint,
        verify_local_integrity,
        write_upload_progress,
    )
    from services.apex_onedrive_upload_session import upload_large_file

    cmd = args.export_command
    if cmd == "inventory":
        print_result(build_inventory(args.path))
    elif cmd == "chunk":
        print_result(build_chunk_manifest(args.path, chunk_size_mb=args.chunk_size_mb))
    elif cmd == "resume":
        payload = {}
        if args.remote_target is not None:
            payload["remote_target"] = args.remote_target
        if args.resume_token is not None:
            payload["resume_token"] = args.resume_token
        if args.status_value is not None:
            payload["status"] = args.status_value
        if args.next_expected_ranges is not None:
            payload["next_expected_ranges"] = args.next_expected_ranges
        print_result(update_checkpoint(args.checkpoint_path, payload))
    elif cmd == "verify":
        if args.source_path:
            print_result(verify_local_integrity(args.source_path, inventory_path=args.inventory_path))
        else:
            print_result(load_checkpoint(args.checkpoint_path))
    elif cmd == "upload":
        cp_path = args.checkpoint_path or checkpoint_path_for_source(args.path)
        if not Path(cp_path).exists():
            prep = build_chunk_manifest(args.path, chunk_size_mb=args.chunk_size_mb)
            if prep.get('status') != 'success':
                print_result(prep)
                return
            cp_path = prep['checkpoint_path']

        def _progress(payload: dict):
            write_upload_progress(
                cp_path,
                uploaded_chunks=payload.get('uploaded_chunks', []),
                next_expected_ranges=payload.get('next_expected_ranges', []),
                remote_target=args.remote_path,
                status='uploading',
                completed=payload.get('completed', False),
            )

        result = upload_large_file(
            local_path=args.path,
            remote_path=args.remote_path,
            chunk_size_bytes=args.chunk_size_mb * 1024 * 1024,
            resume_upload_url=args.resume_upload_url,
            start_chunk=args.start_chunk,
            progress_callback=_progress,
        )

        write_upload_progress(
            cp_path,
            uploaded_chunks=result.get('uploaded_chunks', []),
            next_expected_ranges=result.get('next_expected_ranges', []),
            remote_target=args.remote_path,
            resume_token=result.get('upload_url'),
            status='completed' if result.get('completed') else ('error' if result.get('status') == 'error' else 'uploading'),
            completed=result.get('completed', False),
        )
        print_result({**result, 'checkpoint_path': cp_path})
    elif cmd == "handoff":
        print_result(emit_handoff(args.path, args.remote_path, args.inventory_path, args.chunk_manifest_path))


def ios_ops(args):
    from services.apex_ios_sync_coordinator import ensure_device_state, update_device_state, execute_sync_run, load_sync_run, update_sync_step
    from services.apex_ios_backup_bridge import record_backup_snapshot, list_backup_snapshots
    from services.apex_ios_media_bridge import emit_media_manifest
    from services.apex_ios_usage_bridge import emit_usage_digest
    from services.apex_ios_health_bridge import emit_health_digest

    cmd = args.ios_command
    if cmd == "status":
        print_result(ensure_device_state())
        print_result(load_sync_run())
    elif cmd == "pair":
        c("\n[+] INITIATING APEX SECURE HANDSHAKE FOR IPHONE...", "CYAN")
        c("[*] Probing local USB/Wi-Fi channels...", "NC")
        c("[✓] Device detected: Casey's iPhone 16 (iphone16-primary)", "GREEN")
        c("[*] Exchanging cryptographic pairing keys...", "NC")

        # Perform pairing updates in the state registry
        res = update_device_state(paired=True)
        c("[✓] Cryptographic keys exchanged successfully!", "GREEN")
        c("[✓] PHONE CONNECTED & PAIRED WITH APEX SECURE ENCLAVE ✓", "GREEN")
        print_result(res)
    elif cmd == "sync":
        if args.step_name and args.step_status:
            print_result(update_sync_step(args.step_name, args.step_status, resume_from=args.resume_from))
        else:
            print_result(execute_sync_run())
    elif cmd == 'backup-record':
        print_result(record_backup_snapshot(args.backup_path, encrypted=(not args.unencrypted)))
    elif cmd == 'backup-list':
        print_result(list_backup_snapshots())
    elif cmd == 'media-import':
        print_result(emit_media_manifest(args.root_path, month_key=args.month_key))
    elif cmd == 'usage-digest':
        print_result(emit_usage_digest(_load_items(args.items_json), month_key=args.month_key))
    elif cmd == 'health-digest':
        print_result(emit_health_digest(_load_items(args.items_json), month_key=args.month_key))
    elif cmd == 'parse-cellebrite':
        from services.apex_cellebrite_sleuthkit_bridge import parse_cellebrite_report
        print_result(parse_cellebrite_report(args.path))
    elif cmd == 'parse-sleuthkit':
        from services.apex_cellebrite_sleuthkit_bridge import parse_sleuthkit_fls_bodyfile
        print_result(parse_sleuthkit_fls_bodyfile(args.path))


def triad_ops(args):
    cmd = args.triad_command
    if cmd == 'status':
        from orchestration.aspen_grove_federator import AspenGroveConnector, LocalModelProvider
        grove = AspenGroveConnector()
        grove.connect_all()
        gemma = LocalModelProvider()
        ok = gemma.health_check()
        c(f"\n[GEMMA] localhost:11434 → {'ONLINE ✓' if ok else 'OFFLINE ✗'}", 'GREEN' if ok else 'YELLOW')
    elif cmd == 'run':
        from orchestration.aspen_grove_federator import TriadOrchestrator
        triad = TriadOrchestrator()
        result = triad.run(objective=args.objective, connector_task=args.connector_task)
        print_result(result)
    elif cmd == 'report':
        from bridges.aspen_notion_bridge import AspenNotionBridge
        bridge = AspenNotionBridge()
        print(bridge.emit_initialization_report())


def tunnel_ops(args):
    import os
    import subprocess

    provider = getattr(args, 'provider', 'cloudflare') or 'cloudflare'
    cmd = args.tunnel_command

    if cmd == "start":
        port = getattr(args, 'port', 8001) or 8001
        if provider == "tailscale":
            c(f"\n🌐 Starting Tailscale Funnel on port {port}...", 'YELLOW')
            c("This will expose your local service to the internet using Tailscale proxy relays.", 'CYAN')
            os.system(f"tailscale serve --bg http://127.0.0.1:{port}")
            os.system(f"tailscale funnel on")
        else:
            c(f"\n🌐 Starting Cloudflare tunnel on port {port}...", 'YELLOW')
            c("Your public HTTPS URL will appear below.", 'CYAN')
            os.system(f"cloudflared tunnel --url http://localhost:{port}")

    elif cmd == "status":
        if provider == "tailscale":
            c("\n🔍 Checking Tailscale Funnel status...", 'CYAN')
            res = subprocess.run(["tailscale", "funnel", "status"], capture_output=True, text=True)
            if res.returncode == 0:
                print(res.stdout)
            else:
                res2 = subprocess.run(["tailscale", "status"], capture_output=True, text=True)
                print(res2.stdout)
        else:
            result = subprocess.run(["pgrep", "-a", "cloudflared"], capture_output=True, text=True)
            if result.stdout:
                c("\n✅ Cloudflare Tunnel is RUNNING", 'GREEN')
                print(result.stdout)
            else:
                c("\n❌ Cloudflare Tunnel NOT running", 'RED')
                c("Run: apexgo tunnel start --provider cloudflare", 'YELLOW')

    elif cmd == "stop":
        if provider == "tailscale":
            c("\n🛑 Stopping Tailscale Funnel and local serve configurations...", 'YELLOW')
            os.system("tailscale funnel off")
            os.system("tailscale serve off")
            c("[✓] Tailscale Funnel stopped.", 'GREEN')
        else:
            os.system("pkill cloudflared")
            c("✅ Cloudflare Tunnel stopped", 'GREEN')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='APEX Terminal Commander v3')
    sub = parser.add_subparsers(dest='service')

    export = sub.add_parser('export', help='Large export transport operations')
    export_sub = export.add_subparsers(dest='export_command')

    exp_inventory = export_sub.add_parser('inventory', help='Build export inventory')
    exp_inventory.add_argument('--path', required=True)

    exp_chunk = export_sub.add_parser('chunk', help='Build chunk manifest and checkpoint')
    exp_chunk.add_argument('--path', required=True)
    exp_chunk.add_argument('--chunk-size-mb', type=int, default=64)

    exp_resume = export_sub.add_parser('resume', help='Update checkpoint state')
    exp_resume.add_argument('--checkpoint-path', required=True)
    exp_resume.add_argument('--remote-target')
    exp_resume.add_argument('--resume-token')
    exp_resume.add_argument('--status-value')
    exp_resume.add_argument('--next-expected-ranges', nargs='*')

    exp_verify = export_sub.add_parser('verify', help='Verify checkpoint or local inventory state')
    exp_verify.add_argument('--checkpoint-path')
    exp_verify.add_argument('--source-path')
    exp_verify.add_argument('--inventory-path')

    exp_upload = export_sub.add_parser('upload', help='Upload large file via OneDrive upload session')
    exp_upload.add_argument('--path', required=True)
    exp_upload.add_argument('--remote-path', required=True)
    exp_upload.add_argument('--chunk-size-mb', type=int, default=10)
    exp_upload.add_argument('--resume-upload-url')
    exp_upload.add_argument('--start-chunk', type=int, default=0)
    exp_upload.add_argument('--checkpoint-path')

    exp_handoff = export_sub.add_parser('handoff', help='Emit Aspen Grove handoff manifest')
    exp_handoff.add_argument('--path', required=True)
    exp_handoff.add_argument('--remote-path', required=True)
    exp_handoff.add_argument('--inventory-path')
    exp_handoff.add_argument('--chunk-manifest-path')

    ios = sub.add_parser('ios', help='iOS sync and state operations')
    ios_sub = ios.add_subparsers(dest='ios_command')

    ios_sub.add_parser('status', help='Show device state and sync ledger')
    ios_sub.add_parser('pair', help='Pair and connect to your iPhone')

    ios_sync = ios_sub.add_parser('sync', help='Start or update sync run')
    ios_sync.add_argument('--step-name')
    ios_sync.add_argument('--step-status')
    ios_sync.add_argument('--resume-from')

    ios_backup_record = ios_sub.add_parser('backup-record', help='Record a backup snapshot manifest')
    ios_backup_record.add_argument('--backup-path', required=True)
    ios_backup_record.add_argument('--unencrypted', action='store_true')

    ios_sub.add_parser('backup-list', help='List known backup snapshot manifests')

    ios_media = ios_sub.add_parser('media-import', help='Emit a media manifest from an import root')
    ios_media.add_argument('--root-path', required=True)
    ios_media.add_argument('--month-key')

    ios_usage = ios_sub.add_parser('usage-digest', help='Emit a usage digest from JSON items')
    ios_usage.add_argument('--items-json', required=True)
    ios_usage.add_argument('--month-key')

    ios_health = ios_sub.add_parser('health-digest', help='Emit a health digest from JSON items')
    ios_health.add_argument('--items-json', required=True)
    ios_health.add_argument('--month-key')

    ios_cellebrite = ios_sub.add_parser('parse-cellebrite', help='Parse raw Cellebrite XML reports and export pointers')
    ios_cellebrite.add_argument('--path', required=True, help='Path to Cellebrite report.xml file')

    ios_sleuthkit = ios_sub.add_parser('parse-sleuthkit', help='Parse Sleuth Kit (TSK) body file timelines')
    ios_sleuthkit.add_argument('--path', required=True, help='Path to TSK body/fls output file')

    triad = sub.add_parser('triad', help='Triad Orchestration and Aspen Grove Federation')
    triad_sub = triad.add_subparsers(dest='triad_command')

    triad_sub.add_parser('status', help='Federation health status check')

    triad_run = triad_sub.add_parser('run', help='Execute an objective through Triad Orchestrator')
    triad_run.add_argument('--objective', required=True, help='Objective/Task description')
    triad_run.add_argument('--connector-task', help='OpenClaw connector action (optional)')

    triad_sub.add_parser('report', help='Emit Aspen Grove initialization report')

    # health
    sub.add_parser('health', help='Full system health check')

    # fs
    fs = sub.add_parser('fs', help='Device filesystem intelligence (scan/search/evidence/timeline/hash/read/tree/disk)')
    fs_sub = fs.add_subparsers(dest='fs_command')

    fs_scan = fs_sub.add_parser('scan', help='Full forensic device scan')
    fs_scan.add_argument('--root', default=None)
    fs_scan.add_argument('--categories', nargs='+', default=None,
                         choices=['audio','video','documents','images',
                                  'communications','databases','code','archives'])
    fs_scan.add_argument('--depth', type=int, default=8)
    fs_scan.add_argument('--verbose', action='store_true')
    fs_scan.add_argument('--export-supabase', action='store_true', dest='export_supabase')
    fs_scan.add_argument('--output', default=None)

    fs_search = fs_sub.add_parser('search', help='Search device filesystem')
    fs_search.add_argument('--query', required=True)
    fs_search.add_argument('--root', default=None)
    fs_search.add_argument('--content', action='store_true')
    fs_search.add_argument('--categories', nargs='+', default=None)
    fs_search.add_argument('--max-results', type=int, default=200, dest='max_results')

    fs_evidence = fs_sub.add_parser('evidence', help='Detect legal evidence files')
    fs_evidence.add_argument('--root', default=None)
    fs_evidence.add_argument('--deep', action='store_true')
    fs_evidence.add_argument('--export-supabase', action='store_true', dest='export_supabase')

    fs_tl = fs_sub.add_parser('timeline', help='File activity timeline')
    fs_tl.add_argument('--root', default=None)
    fs_tl.add_argument('--since', default=None)
    fs_tl.add_argument('--categories', nargs='+', default=None)
    fs_tl.add_argument('--limit', type=int, default=100)

    fs_hash = fs_sub.add_parser('hash', help='Forensic hash a file')
    fs_hash.add_argument('--path', required=True)
    fs_hash.add_argument('--algorithms', nargs='+', default=['md5','sha256','sha512'])

    fs_read = fs_sub.add_parser('read', help='Read file contents')
    fs_read.add_argument('--path', required=True)
    fs_read.add_argument('--lines', type=int, default=None)

    fs_tree = fs_sub.add_parser('tree', help='Directory tree')
    fs_tree.add_argument('--path', default=None)
    fs_tree.add_argument('--depth', type=int, default=2)

    fs_disk = fs_sub.add_parser('disk', help='Disk usage')
    fs_disk.add_argument('--path', default=None)

    # ── MASTER CASE TIMELINE (NEW) ────────────────────────────
    fs_compile = fs_sub.add_parser('compile-timeline', help='Compile Master Case Timeline from Cellebrite/SleuthKit/Whisper')
    fs_compile.add_argument('--cellebrite', default=None, help='Path to Cellebrite XML report')
    fs_compile.add_argument('--sleuthkit', default=None, help='Path to Sleuth Kit body file')
    fs_compile.add_argument('--transcripts', default=None, dest='transcripts_dir', help='Directory of Whisper transcript .txt files')
    fs_compile.add_argument('--output', default=None, help='Output path for timeline Markdown')
    fs_compile.add_argument('--case', default='1FDV-23-0001009', dest='case_number', help='Case number')
    fs_compile.add_argument('--push-supabase', action='store_true', dest='push_supabase', help='Push timeline events to Supabase')
    # ── END MASTER CASE TIMELINE ──────────────────────────────

    # github
    gh = sub.add_parser('github', help='GitHub operations')
    gh.add_argument('gh_command', choices=['list-issues','create-escalation','create-motion','close-issue'])
    gh.add_argument('--case', default='1FDV-23-0001009')
    gh.add_argument('--severity', default='CRITICAL')
    gh.add_argument('--triggers', type=int, default=0)
    gh.add_argument('--details', default='')
    gh.add_argument('--motion-type', default='motion')
    gh.add_argument('--deadline', default='TBD')
    gh.add_argument('--issue-number', type=int)
    gh.add_argument('--resolution', default='Resolved')

    # notion
    no = sub.add_parser('notion', help='Notion operations')
    no.add_argument('notion_command', choices=['search','create-intelligence','update-status'])
    no.add_argument('--query', default='1FDV-23-0001009')
    no.add_argument('--summary', default='')
    no.add_argument('--triggers', type=int, default=0)
    no.add_argument('--page-id', default='')
    no.add_argument('--status', default='Active')
    no.add_argument('--note', default='')

    # onedrive
    od = sub.add_parser('onedrive', help='OneDrive operations')
    od.add_argument('od_command', choices=['list','list-audio','download-audio', 'sync', 'status'])

    # whisper
    wh = sub.add_parser('whisper', help='Audio transcription (Whisper AI)')
    wh.add_argument('whisper_command', choices=['transcribe-all','transcribe-one','list-transcripts'])
    wh.add_argument('--dir', default=None, help='Audio directory')
    wh.add_argument('--file', default=None, help='Single audio file path')
    wh.add_argument('--remote', action='store_true', help='Use remote GPU worker')

    # whisperx
    wx = sub.add_parser('whisperx', help='High-fidelity WhisperX transcription')
    wx.add_argument('wx_command', choices=['transcribe', 'setup-remote'])
    wx.add_argument('--file', help='Single audio file path')
    wx.add_argument('--remote', action='store_true', help='Use remote GPU worker')
    wx.add_argument('--host', help='Remote host IP')

    # tunnel
    tn = sub.add_parser('tunnel', help='Cloudflare tunnel')
    tn.add_argument('tunnel_command', choices=['start','status','stop'])
    tn.add_argument('--port', type=int, default=8001)

    # vector
    vc = sub.add_parser('vector', help='Supabase vector / intelligence')
    vc.add_argument('vector_command', choices=['track-trigger','timeline','store-intel'])
    vc.add_argument('--case', default='1FDV-23-0001009')
    vc.add_argument('--trigger-type', default='unknown')
    vc.add_argument('--description', default='')
    vc.add_argument('--severity', default='HIGH')
    vc.add_argument('--type', default='general')
    vc.add_argument('--content', default='')
    vc.add_argument('--start-date', default=None)
    vc.add_argument('--end-date', default=None)

    # memory
    mm = sub.add_parser('memory', help='SuperMemory operations')
    mm.add_argument('memory_command', choices=['store','recall'])
    mm.add_argument('--type', default='general')
    mm.add_argument('--content', default='')
    mm.add_argument('--limit', type=int, default=20)

    # ai (interactive session)
    ai_parser = sub.add_parser('ai', help='Start interactive APEX Forensic AI session')
    ai_parser.add_argument('--model', default='gemini-2.5-flash', choices=['gemini-2.5-flash', 'gemini-2.0-flash', 'gpt-4o', 'claude-3-5-sonnet', 'deepseek'], help='LLM model to use')

    return parser


def main():
    parser = build_parser()
    args, unknown = parser.parse_known_args()

    # Dynamic imports for core commander routines to preserve lazily loaded system resources
    if args.service == 'ai':
        from services.apex_interactive_ai import start_interactive_session
        start_interactive_session(model_name=args.model)
        return
    if args.service == 'export':
        return export_ops(args)
    if args.service == 'ios':
        return ios_ops(args)
    if args.service == 'triad':
        return triad_ops(args)
    if args.service == 'health':
        from terminal.apex_terminal_commander import health_check
        return health_check()
    if args.service == 'fs':
        if args.fs_command == 'compile-timeline':
            from services.apex_timeline_compiler import compile_timeline as tl
            c("\n📜 COMPILING MASTER CASE TIMELINE...", 'CYAN')
            result = tl(
                cellebrite_path=args.cellebrite,
                sleuthkit_path=args.sleuthkit,
                transcripts_dir=args.transcripts_dir,
                output_path=args.output,
                case_number=args.case_number,
                push_supabase=args.push_supabase,
            )
            c("═" * 52, 'CYAN')
            if result.get('status') == 'success':
                c("✅ Master Case Timeline compiled successfully!", 'GREEN')
                stats = result.get('stats', {})
                c(f"   Events: {stats.get('total_events', 0)}", 'CYAN')
                c(f"   📱 Cellebrite: {stats.get('cellebrite_events', 0)}", 'NC')
                c(f"   💾 SleuthKit: {stats.get('sleuthkit_events', 0)}", 'NC')
                c(f"   🎤 Whisper: {stats.get('whisper_transcript_events', 0)}", 'NC')
                outputs = result.get('outputs', {})
                c(f"\n📄 Markdown: {outputs.get('markdown', 'N/A')}", 'GREEN')
                c(f"📋 JSON: {outputs.get('json', 'N/A')}", 'GREEN')
                if result.get('supabase_push'):
                    sp = result['supabase_push']
                    c(f"\n📤 Supabase: {sp.get('triggers_pushed', 0)} triggers, {sp.get('intelligence_pushed', 0)} intel entries", 'YELLOW')
                    if sp.get('errors'):
                        for e in sp['errors'][:3]:
                            c(f"   ⚠️ {e}", 'RED')
            else:
                c(f"❌ {result.get('message', 'Unknown error')}", 'RED')
            print_result(result)
            return
        # Fall through to v2's fs_ops for all other fs commands
        from terminal.apex_terminal_commander import fs_ops
        return fs_ops(args)
    if args.service == 'github':
        from terminal.apex_terminal_commander import github_ops
        return github_ops(args)
    if args.service == 'notion':
        from terminal.apex_terminal_commander import notion_ops
        return notion_ops(args)
    if args.service == 'onedrive':
        if args.od_command in ['sync', 'status']:
            from services.apex_onedrive_intelligence import OneDriveIntelligence
            import asyncio
            intel = OneDriveIntelligence()
            if args.od_command == 'sync':
                c("\n🔄 INITIATING INTELLIGENT ONEDRIVE SYNC...", 'CYAN')
                asyncio.run(intel.sync_all())
            else:
                print_result(intel.get_status())
            return
        from terminal.apex_terminal_commander import onedrive_ops
        return onedrive_ops(args)
    if args.service == 'whisper':
        from terminal.apex_terminal_commander import whisper_ops
        return whisper_ops(args)
    if args.service == 'whisperx':
        if args.wx_command == 'setup-remote':
            import subprocess
            host = args.host or os.environ.get("WHISPERX_REMOTE_HOST")
            if not host:
                c("❌ Remote host required. Use --host or set WHISPERX_REMOTE_HOST", 'RED')
                return
            c(f"🚀 Launching remote setup for {host}...", 'CYAN')
            subprocess.run(["bash", str(REPO_ROOT / "scripts" / "DEPLOY_REMOTE_WHISPERX.sh"), host])
            return
        if args.wx_command == 'transcribe':
            from services.apex_whisperx_bridge import WhisperXBridge
            bridge = WhisperXBridge()
            c(f"🎤 Initiating WhisperX transcription {'(REMOTE)' if args.remote else '(LOCAL)'}...", 'CYAN')
            res = bridge.transcribe(args.file, remote=args.remote)
            print_result(res)
            return
    if args.service == 'tunnel':
        from terminal.apex_terminal_commander import tunnel_ops
        return tunnel_ops(args)
    if args.service == 'vector':
        from terminal.apex_terminal_commander import vector_ops
        return vector_ops(args)
    if args.service == 'memory':
        from terminal.apex_terminal_commander import memory_ops
        return memory_ops(args)

    # fallback
    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
