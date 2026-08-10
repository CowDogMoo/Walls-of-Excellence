#!/usr/bin/env bash
#
# Regenerate the marked sections of README.md from repository state.
#
# Sections (between "<!-- BEGIN GENERATED: <name> -->" markers):
#   apps      - applications under kubernetes/apps, grouped by namespace
#   docs      - guides under docs/
#   tasks     - root tasks and task categories from Taskfile.yaml
#   workflows - GitHub Actions workflows
#
# Only tracked files (git ls-files) feed the output so local and CI runs
# agree regardless of untracked files or submodule state. Exits non-zero
# when README.md changed so pre-commit surfaces the drift.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

README="README.md"

if ! command -v yq > /dev/null 2>&1; then
    echo "Error: yq is required to regenerate ${README}" >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

# First "# " heading of a markdown file, falling back to its path.
md_title() {
    local file="$1" title
    title="$(awk '/^# / { sub(/^# /, ""); print; exit }' "${file}")"
    echo "${title:-${file}}"
}

gen_apps() {
    local ns app prev_ns="" row_apps="" ns_count=0 app_count=0 table=""

    while IFS=$'\t' read -r ns app; do
        app_count=$((app_count + 1))
        if [[ ${ns} != "${prev_ns}" ]]; then
            if [[ -n ${prev_ns} ]]; then
                table+="| \`${prev_ns}\` | ${row_apps} |"$'\n'
            fi
            ns_count=$((ns_count + 1))
            prev_ns="${ns}"
            row_apps=""
        fi
        if [[ -n ${row_apps} ]]; then
            row_apps+=", "
        fi
        row_apps+="[${app}](kubernetes/apps/${ns}/${app})"
    done < <(git ls-files 'kubernetes/apps/*' \
        | awk -F/ 'NF >= 5 { print $3 "\t" $4 }' \
        | sort -u)
    if [[ -n ${prev_ns} ]]; then
        table+="| \`${prev_ns}\` | ${row_apps} |"$'\n'
    fi

    echo "Flux reconciles **${app_count} applications** across" \
        "**${ns_count} namespaces** from [\`kubernetes/apps/\`](kubernetes/apps)."
    echo ""
    echo "| Namespace | Applications |"
    echo "| --------- | ------------ |"
    printf '%s' "${table}"
}

gen_docs() {
    local f
    while IFS= read -r f; do
        printf -- '- [%s](%s)\n' "$(md_title "${f}")" "${f}"
    done < <(git ls-files 'docs/*.md' | sort)
}

gen_tasks() {
    local root_tasks name src text url
    # shellcheck disable=SC2016  # literal backticks, not command substitution
    root_tasks="$(yq '.tasks | keys | .[]' Taskfile.yaml \
        | grep -v '^#' \
        | sed 's/^/`/; s/$/`/' \
        | paste -s -d ',' - \
        | sed 's/,/, /g')"

    echo "Root tasks (run as \`task <name>\`): ${root_tasks}." \
        | fold -s -w 79 \
        | sed 's/ *$//'
    echo ""
    echo "| Category | Defined in |"
    echo "| -------- | ---------- |"
    while IFS=$'\t' read -r name src; do
        if [[ ${src} == https://raw.githubusercontent.com/* ]]; then
            url="$(echo "${src}" \
                | sed -E 's|^https://raw\.githubusercontent\.com/([^/]+/[^/]+)/([^/]+)/|https://github.com/\1/blob/\2/|')"
            text="$(echo "${src}" \
                | sed -E 's|^https://raw\.githubusercontent\.com/([^/]+/[^/]+)/[^/]+/(.*)/Taskfile\.ya?ml$|\1/\2|')"
        else
            url="${src#./}"
            text="$(dirname "${url}")"
        fi
        echo "| \`${name}:*\` | [${text}](${url}) |"
    done < <(yq '.includes | to_entries | .[]
        | .key + "\t" + ((.value | select(kind == "map") | .taskfile) // .value)' \
        Taskfile.yaml | sort)
}

gen_workflows() {
    local f name
    while IFS= read -r f; do
        name="$(yq '.name // ""' "${f}")"
        printf -- '- [%s](%s)\n' "${name:-$(basename "${f}")}" "${f}"
    done < <(git ls-files '.github/workflows/*.y*ml' | sort)
}

replace_block() {
    local name="$1" content_file="$2"
    local begin="<!-- BEGIN GENERATED: ${name} -->"
    local end="<!-- END GENERATED: ${name} -->"
    local begin_line end_line

    begin_line="$(grep -nxF "${begin}" "${README}" | head -n1 | cut -d: -f1 || true)"
    end_line="$(grep -nxF "${end}" "${README}" | head -n1 | cut -d: -f1 || true)"
    if [[ -z ${begin_line} || -z ${end_line} ]] || ((begin_line >= end_line)); then
        echo "Error: missing or malformed markers for section '${name}' in ${README}" >&2
        exit 1
    fi

    {
        head -n "${begin_line}" "${README}"
        echo ""
        cat "${content_file}"
        echo ""
        tail -n +"${end_line}" "${README}"
    } > "${TMP_DIR}/readme"
    mv "${TMP_DIR}/readme" "${README}"
}

main() {
    local before="${TMP_DIR}/before" section
    cp "${README}" "${before}"

    for section in apps docs tasks workflows; do
        "gen_${section}" > "${TMP_DIR}/${section}.md"
        replace_block "${section}" "${TMP_DIR}/${section}.md"
    done

    if ! cmp -s "${before}" "${README}"; then
        echo "Regenerated sections in ${README}; review and re-stage it."
        exit 1
    fi
}

main "$@"
