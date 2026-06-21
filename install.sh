#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PACKAGE_IDS=("content-create" "tkshop-query" "social-monitor" "video-understand" "tk-blacklist")
PACKAGE_NAMES=("Content Create - 商品图、参考图、电商视频、爆款复刻" "TKShop Query - TK 店铺数据查询和经营分析" "Social Monitor - TikTok/Instagram 达人竞品监控、素材数据和评论导出" "Video Understand - 视频理解、内容分析与复刻提示词生成" "TK Blacklist - TK 达人黑名单查询")
PACKAGE_DIRS=("packages/content-create" "packages/tkshop-query" "packages/social-monitor" "packages/video-understand" "packages/tk-blacklist")
CODEX_NAMES=("lingtu-content-create" "lingtu-tkshop-query" "lingtu-social-monitor" "lingtu-video-understand" "lingtu-tk-blacklist")

usage() {
  cat <<'USAGE'
Usage:
  ./install.sh
  ./install.sh auto [destination] [packages...]
  ./install.sh codex [packages...]
  ./install.sh claude [destination] [packages...]
  ./install.sh cursor [destination] [packages...]
  ./install.sh openclaw [destination] [packages...]
  ./install.sh openai [destination] [packages...]
  ./install.sh dify [destination] [packages...]

Examples:
  ./install.sh
  ./install.sh codex all
  ./install.sh codex content-create tkshop-query social-monitor
  ./install.sh claude /path/to/project content-create
  ./install.sh cursor /path/to/project all
  ./install.sh openclaw /path/to/project all

Targets:
  auto    Detect the current AI platform and install the matching adapter.
  codex   Install selected packages as Codex skills under ~/.codex/skills.
  claude  Install selected packages and CLAUDE.md into a project.
  cursor  Install selected packages and AGENTS.md into a project.
  openclaw  Install selected packages and AGENTS.md into an OpenClaw project.
  openai  Export selected packages with an OpenAI adapter prompt.
  dify    Export selected packages with Dify notes.

Packages:
  all
  content-create
  tkshop-query
  social-monitor
  video-understand
  tk-blacklist
USAGE
}

detect_platform() {
  if [[ -n "${CLAUDE_CODE:-}" ]] || [[ -d ".claude" ]] || [[ -f "CLAUDE.md" ]]; then
    echo "claude"
    return
  fi

  if [[ -d "${CODEX_SKILLS_DIR:-$HOME/.codex}" ]]; then
    echo "codex"
    return
  fi

  if [[ -d ".cursor" ]]; then
    echo "cursor"
    return
  fi

  if [[ -d ".openclaw" ]] || [[ -n "${OPENCLAW:-}" ]]; then
    echo "openclaw"
    return
  fi

  echo ""
}

copy_dir() {
  local src="$1"
  local dst="$2"
  mkdir -p "$dst"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --delete-excluded \
      --exclude '.git' \
      --exclude '.DS_Store' \
      --exclude '__pycache__' \
      --exclude '*.pyc' \
      "$src"/ "$dst"/
  else
    mkdir -p "$dst"
    cp -R "$src"/. "$dst"/
    find "$dst" -name .git -type d -prune -exec rm -rf {} +
    find "$dst" -name .DS_Store -type f -delete
    find "$dst" -name __pycache__ -type d -prune -exec rm -rf {} +
    find "$dst" -name '*.pyc' -type f -delete
  fi
}

package_index() {
  local id="$1"
  local i
  for i in "${!PACKAGE_IDS[@]}"; do
    if [[ "${PACKAGE_IDS[$i]}" == "$id" ]]; then
      echo "$i"
      return 0
    fi
  done
  return 1
}

print_packages() {
  local i
  echo "Available packages:"
  for i in "${!PACKAGE_IDS[@]}"; do
    printf '  %s) %s [%s]\n' "$((i + 1))" "${PACKAGE_NAMES[$i]}" "${PACKAGE_IDS[$i]}"
  done
  echo "  all) Install all packages"
}

select_packages_interactive() {
  print_packages >&2
  echo >&2
  printf 'Select packages to install (example: 1,2 or all): ' >&2
  local answer
  read -r answer
  answer="${answer:-all}"
  normalize_packages "$answer"
}

normalize_packages() {
  local raw=("$@")
  local selected=()
  local token

  if [[ "${#raw[@]}" -eq 0 ]]; then
    if [[ -t 0 ]]; then
      select_packages_interactive
      return
    fi
    raw=("all")
  fi

  for token in "${raw[@]}"; do
    token="${token//,/ }"
    local part
    for part in $token; do
      case "$part" in
        all|"*")
          printf '%s\n' "${PACKAGE_IDS[@]}"
          return
          ;;
        1|2|3|4|5|6|7|8|9)
          local idx=$((part - 1))
          if [[ "$idx" -ge 0 && "$idx" -lt "${#PACKAGE_IDS[@]}" ]]; then
            selected+=("${PACKAGE_IDS[$idx]}")
          else
            echo "Unknown package number: $part" >&2
            exit 1
          fi
          ;;
        *)
          if package_index "$part" >/dev/null; then
            selected+=("$part")
          else
            echo "Unknown package: $part" >&2
            print_packages >&2
            exit 1
          fi
          ;;
      esac
    done
  done

  if [[ "${#selected[@]}" -eq 0 ]]; then
    echo "No packages selected." >&2
    exit 1
  fi

  printf '%s\n' "${selected[@]}" | awk '!seen[$0]++'
}

install_selected_packages_to_dir() {
  local dst_root="$1"
  shift
  local id idx
  for id in "$@"; do
    idx="$(package_index "$id")"
    copy_dir "$ROOT_DIR/${PACKAGE_DIRS[$idx]}" "$dst_root/$id"
    echo "Installed package $id to $dst_root/$id"
  done
}

generate_agent_doc() {
  local target="$1"
  local file="$2"
  shift 2

  {
    if [[ "$target" == "claude" ]]; then
      echo "# Lingtu AI Capabilities"
    else
      echo "# Lingtu AI Agent Instructions"
    fi
    echo
    echo "Use the selected Lingtu AI packages from this project when the user requests matching capabilities."
    echo
    echo "## Repository Source"
    echo
    echo "- GitHub: https://github.com/ailingtu/lingtu-skills"
    echo "- When the user asks to update Lingtu AI skills, pull the latest version from this repository."
    echo
    echo "## Installed Packages"
    echo
    local id idx
    for id in "$@"; do
      idx="$(package_index "$id")"
      echo "- \`.lingtu-agent-kit/packages/$id\`: ${PACKAGE_NAMES[$idx]}"
    done
    echo
    echo "## Shared Rules"
    echo
    echo "- Require \`LINGTU_API_KEY\` in the process environment."
    echo "- Send the key as request header \`x-api-key\`."
    echo "- Start from each package's \`SKILL.md\` instruction file."
    echo "- Read the package \`references/api.md\` before changing endpoint paths, request fields, response fields, or status handling."
    echo "- Prefer package scripts over ad hoc API calls."
    echo "- Do not write customer API keys or private business data into source files."
  } > "$file"
}

install_codex() {
  local skills_dir="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
  local id idx
  for id in "$@"; do
    idx="$(package_index "$id")"
    copy_dir "$ROOT_DIR/${PACKAGE_DIRS[$idx]}" "$skills_dir/${CODEX_NAMES[$idx]}"
    echo "Installed Codex skill ${CODEX_NAMES[$idx]} to $skills_dir/${CODEX_NAMES[$idx]}"
  done
}

install_project_adapter() {
  local target="$1"
  local dest="$2"
  shift 2

  case "$target" in
    claude)
      mkdir -p "$dest/.lingtu-agent-kit/packages"
      install_selected_packages_to_dir "$dest/.lingtu-agent-kit/packages" "$@"
      generate_agent_doc claude "$dest/CLAUDE.md" "$@"
      echo "Installed Claude adapter to $dest/CLAUDE.md"
      ;;
    cursor)
      mkdir -p "$dest/.lingtu-agent-kit/packages"
      install_selected_packages_to_dir "$dest/.lingtu-agent-kit/packages" "$@"
      generate_agent_doc cursor "$dest/AGENTS.md" "$@"
      echo "Installed Cursor adapter to $dest/AGENTS.md"
      ;;
    openclaw)
      mkdir -p "$dest/.lingtu-agent-kit/packages"
      install_selected_packages_to_dir "$dest/.lingtu-agent-kit/packages" "$@"
      generate_agent_doc openclaw "$dest/AGENTS.md" "$@"
      echo "Installed OpenClaw adapter to $dest/AGENTS.md"
      ;;
    openai)
      mkdir -p "$dest/lingtu-openai-adapter"
      copy_dir "$ROOT_DIR/adapters/openai" "$dest/lingtu-openai-adapter"
      install_selected_packages_to_dir "$dest/lingtu-openai-adapter/packages" "$@"
      echo "Installed OpenAI adapter to $dest/lingtu-openai-adapter"
      ;;
    dify)
      mkdir -p "$dest/lingtu-dify-adapter"
      copy_dir "$ROOT_DIR/adapters/dify" "$dest/lingtu-dify-adapter"
      install_selected_packages_to_dir "$dest/lingtu-dify-adapter/packages" "$@"
      echo "Exported Dify adapter to $dest/lingtu-dify-adapter"
      ;;
  esac
}

main() {
  local target="${1:-auto}"
  shift || true

  case "$target" in
    ""|-h|--help|help)
      usage
      exit 0
      ;;
  esac

  if [[ "$target" == "auto" ]]; then
    local detected
    detected="$(detect_platform)"
    if [[ -z "$detected" ]]; then
      echo "Cannot auto-detect the AI platform. Please specify a target explicitly."
      usage
      exit 1
    fi
    echo "Auto-detected platform: $detected"
    target="$detected"
  fi

  local dest=""
  case "$target" in
    codex)
      ;;
    claude|cursor|openclaw|openai|dify)
      if [[ "${1:-}" != "" ]] && [[ "${1:-}" != "all" ]] && ! package_index "${1:-}" >/dev/null 2>&1 && ! [[ "${1:-}" =~ ^[0-9,]+$ ]]; then
        dest="$1"
        shift
      else
        dest="$(pwd)"
        echo "No target path given, using current directory: $dest"
      fi
      mkdir -p "$dest"
      ;;
    *)
      echo "Unknown target: $target"
      usage
      exit 1
      ;;
  esac

  local selected=()
  while IFS= read -r package_id; do
    selected+=("$package_id")
  done < <(normalize_packages "$@")

  echo
  echo "Selected packages:"
  printf '  - %s\n' "${selected[@]}"
  echo

  case "$target" in
    codex)
      install_codex "${selected[@]}"
      ;;
    claude|cursor|openclaw|openai|dify)
      install_project_adapter "$target" "$dest" "${selected[@]}"
      ;;
  esac
}

main "$@"
