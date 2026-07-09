# Shared helpers — sourced by prepare-commit-msg and commit-msg.
# Blocks/strips automation co-author trailers from commit messages.

_AGENT_COAUTHOR_RE='^[Cc]o-[Aa]uthored-[Bb]y:.*(cursor|cursoragent|claude|anthropic|noreply@anthropic)'

_AGENT_FLAFF_RE='^(🤖[[:space:]]*)?[Gg]enerated with.*[Cc]laude'

strip_agent_trailers() {
    _msg="$1"
    _tmp="$(mktemp "${TMPDIR:-/tmp}/git-commit-msg.XXXXXX")" || return 1
    _kept="$(mktemp "${TMPDIR:-/tmp}/git-commit-kept.XXXXXX")" || { rm -f "$_tmp"; return 1; }

    grep -viE "$_AGENT_COAUTHOR_RE|$_AGENT_FLAFF_RE" "$_msg" > "$_kept" || true

    awk 'NF{p=1} p' "$_kept" > "$_tmp"
    mv "$_tmp" "$_kept"
    cp "$_kept" "$_msg"
    rm -f "$_kept"
}

has_agent_trailers() {
    grep -qiE "$_AGENT_COAUTHOR_RE|$_AGENT_FLAFF_RE" "$1"
}
