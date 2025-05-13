The following steps are tested on Ubuntu.
### Install dependencies:
```
sudo apt-get install build-essential cmake curl file g++-multilib gcc-multilib git libcap-dev libgoogle-perftools-dev libncurses5-dev libsqlite3-dev libtcmalloc-minimal4 python3-pip unzip graphviz doxygen
```
You should also install lit to enable testing, tabulate to support additional features in klee-stats and wllvm to make it easier to compile programs to LLVM bitcode:
```
sudo apt-get install python3-tabulate
sudo pip3 install lit wllvm
```
### Install LLVM 14:
```
sudo apt-get install clang-14 llvm-14 llvm-14-dev llvm-14-tools
```
### Install constraint solver Z3:
```
git clone https://github.com/Z3Prover/z3.git
cd z3
python3 scripts/mk_make.py
cd build
make
sudo make install
cd ../..
```
### Build uClibc and the POSIX environment model: 
By default, KLEE works on closed programs (programs without external code, such as C library functions). However, if you want to use KLEE to run real programs, you will want to enable the KLEE POSIX runtime, which is built on top of the uClibc C library.
```
git clone https://github.com/klee/klee-uclibc.git
cd klee-uclibc
./configure --make-llvm-lib --with-cc clang-14 --with-llvm-config llvm-config-14
make -j2
cd ..
```
### Build KLEE
Get KLEE source:
```
git clone https://github.com/klee/klee.git
```
KLEE must be built “out of source”:
```
mkdir klee_build
cd klee_build
cmake -DENABLE_SOLVER_Z3=ON -DENABLE_POSIX_RUNTIME=ON -DKLEE_UCLIBC_PATH=../klee-uclibc -DLLVM_CONFIG_BINARY=/usr/bin/llvm-config-14 ../klee
make
```
### Link the executables [Optional]
If you have to execute the generated programs repeatedly, it is helpful to have shortcuts for them.
```
nano ~/.bashrc
```
Put these lines at the end of your ~/.bashrc. Replace the paths corresponding to your directory structure.
```
alias       klee="~/klee_build/bin/klee"
alias       ktest-tool="~/klee_build/bin/ktest-tool"
```
