# Detect script directory (works in both bash and zsh)
if [ -n "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
elif [ -n "${ZSH_VERSION}" ]; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${(%):-%x}" )" &> /dev/null && pwd )
fi

# Use CONDA_ENV_NAME if provided, otherwise default to "hssim"
CONDA_ENV_NAME=${CONDA_ENV_NAME:-hssim}
echo "conda environment name is set to: $CONDA_ENV_NAME"

source ${SCRIPT_DIR}/source_common.sh
if [ -f "${CONDA_ROOT}/bin/activate" ]; then
    source "${CONDA_ROOT}/bin/activate" "$CONDA_ENV_NAME"
elif [ -f "${CONDA_ROOT}/envs/${CONDA_ENV_NAME}/bin/activate" ]; then
    # Offline conda-pack bundles may contain only the requested environment.
    source "${CONDA_ROOT}/envs/${CONDA_ENV_NAME}/bin/activate"
else
    echo "Conda environment not found: ${CONDA_ROOT}/envs/${CONDA_ENV_NAME}" >&2
    return 1 2>/dev/null || exit 1
fi
export OMNI_KIT_ACCEPT_EULA=1
