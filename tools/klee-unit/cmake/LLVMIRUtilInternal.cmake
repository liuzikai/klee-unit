
# internal utility macros/functions

function(fatal message_txt)
  message(FATAL_ERROR "${message_txt}")
endfunction()


function(debug message_txt)
  if($ENV{LLVMIR_CMAKE_DEBUG})
    message(STATUS "[DEBUG] ${message_txt}")
  endif()
endfunction()


macro(catuniq lst)
  list(APPEND ${lst} ${ARGN})
  if(${lst})
    list(REMOVE_DUPLICATES ${lst})
  endif()
endmacro()


# internal implementation detail macros/functions

macro(llvmir_setup)
  set(LLVMIR_DIR "llvm-ir")

  set(LLVMIR_COMPILER "")
  set(LLVMIR_OPT "opt")
  set(LLVMIR_LINK "llvm-link")
  set(LLVMIR_ASSEMBLER "llvm-as")
  set(LLVMIR_DISASSEMBLER "llvm-dis")

  set(LLVMIR_BINARY_FMT_SUFFIX "bc")
  set(LLVMIR_TEXT_FMT_SUFFIX "ll")

  set(LLVMIR_BINARY_TYPE "LLVMIR_BINARY")
  set(LLVMIR_TEXT_TYPE "LLVMIR_TEXT")

  set(LLVMIR_TYPES ${LLVMIR_BINARY_TYPE} ${LLVMIR_TEXT_TYPE})
  set(LLVMIR_FMT_SUFFICES ${LLVMIR_BINARY_FMT_SUFFIX} ${LLVMIR_TEXT_FMT_SUFFIX})

  set(LLVMIR_COMPILER_IDS "Clang" "AppleClang")

  message(STATUS "LLVM IR Utils version: ${LLVM_IR_UTIL_VERSION}")

  define_property(TARGET PROPERTY LLVMIR_TYPE
    BRIEF_DOCS "type of LLVM IR file"
    FULL_DOCS "type of LLVM IR file")
  define_property(TARGET PROPERTY LLVMIR_DIR
    BRIEF_DOCS "Input /output directory for LLVM IR files"
    FULL_DOCS "Input /output directory for LLVM IR files")
  define_property(TARGET PROPERTY LLVMIR_FILES
    BRIEF_DOCS "list of LLVM IR files"
    FULL_DOCS "list of LLVM IR files")
endmacro()


macro(llvmir_set_compiler linker_language)
  if("${LLVMIR_COMPILER}" STREQUAL "")
    set(LLVMIR_COMPILER ${CMAKE_${linker_language}_COMPILER})
    set(LLVMIR_COMPILER_ID ${CMAKE_${linker_language}_COMPILER_ID})

    list(FIND LLVMIR_COMPILER_IDS ${LLVMIR_COMPILER_ID} found)

    if(found EQUAL -1)
      fatal("LLVM IR compiler ID ${LLVMIR_COMPILER_ID} is not in \
      ${LLVMIR_COMPILER_IDS}")
    endif()
  endif()
endmacro()


function(llvmir_check_target_properties_impl trgt)
  if(NOT TARGET ${trgt})
    fatal("Cannot attach to non-existing target: ${trgt}.")
  endif()

  foreach(prop ${ARGN})
    # equivalent to
    # if(DEFINED prop AND prop STREQUAL "")
    set(is_def TRUE)
    set(is_set TRUE)

    # this seems to not be working for targets defined with builtins
    #get_property(is_def TARGET ${trgt} PROPERTY ${prop} DEFINED)

    get_property(is_set TARGET ${trgt} PROPERTY ${prop} SET)

    if(NOT is_def)
      fatal("property ${prop} for target ${trgt} must be defined.")
    endif()

    if(NOT is_set)
      fatal("property ${prop} for target ${trgt} must be set.")
    endif()
  endforeach()
endfunction()


function(llvmir_check_non_llvmir_target_properties trgt)
  set(props SOURCES LINKER_LANGUAGE)

  llvmir_check_target_properties_impl(${trgt} ${props})
endfunction()


function(llvmir_check_target_properties trgt)
  set(props LINKER_LANGUAGE LLVMIR_DIR LLVMIR_FILES LLVMIR_TYPE)

  llvmir_check_target_properties_impl(${trgt} ${props})
endfunction()


function(llvmir_extract_compile_defs_properties out_compile_defs from)
  set(defs "")
  set(compile_defs "")
  set(prop_name "COMPILE_DEFINITIONS")

  # per directory
  get_property(defs DIRECTORY PROPERTY ${prop_name})
  foreach(def ${defs})
    list(APPEND compile_defs -D${def})
  endforeach()

  get_property(defs DIRECTORY PROPERTY ${prop_name}_${CMAKE_BUILD_TYPE})
  foreach(def ${defs})
    list(APPEND compile_defs -D${def})
  endforeach()

  # per target
  if(TARGET ${from})
    get_property(defs TARGET ${from} PROPERTY ${prop_name})
    foreach(def ${defs})
      list(APPEND compile_defs -D${def})
    endforeach()

    get_property(defs TARGET ${from} PROPERTY ${prop_name}_${CMAKE_BUILD_TYPE})
    foreach(def ${defs})
      list(APPEND compile_defs -D${def})
    endforeach()

    get_property(defs TARGET ${from} PROPERTY INTERFACE_${prop_name})
    foreach(def ${defs})
      list(APPEND compile_defs -D${def})
    endforeach()
  else()
    # per file
    get_property(defs SOURCE ${from} PROPERTY ${prop_name})
    foreach(def ${defs})
      list(APPEND compile_defs -D${def})
    endforeach()

    get_property(defs SOURCE ${from} PROPERTY ${prop_name}_${CMAKE_BUILD_TYPE})
    foreach(def ${defs})
      list(APPEND compile_defs -D${def})
    endforeach()
  endif()

  list(REMOVE_DUPLICATES compile_defs)

  debug("@llvmir_extract_compile_defs_properties ${from}: ${compile_defs}")

  set(${out_compile_defs} ${compile_defs} PARENT_SCOPE)
endfunction()


function(llvmir_extract_compile_option_properties out_compile_options trgt)
  set(options "")
  set(compile_options "")
  set(prop_name "COMPILE_OPTIONS")

  # per directory
  get_property(options DIRECTORY PROPERTY ${prop_name})
  foreach(opt ${options})
    list(APPEND compile_options ${opt})
  endforeach()

  # per target
  get_property(options TARGET ${trgt} PROPERTY ${prop_name})
  foreach(opt ${options})
    list(APPEND compile_options ${opt})
  endforeach()

  get_property(options TARGET ${trgt} PROPERTY INTERFACE_${prop_name})
  foreach(opt ${options})
    list(APPEND compile_options ${opt})
  endforeach()

  list(REMOVE_DUPLICATES compile_options)

  debug("@llvmir_extract_compile_option_properties ${trgt}: ${compile_options}")

  set(${out_compile_options} ${compile_options} PARENT_SCOPE)
endfunction()


function(llvmir_extract_include_dirs_properties out_include_dirs trgt)
  set(dirs "")
  set(prop_name "INCLUDE_DIRECTORIES")

  # per directory
  get_property(dirs DIRECTORY PROPERTY ${prop_name})
  foreach(dir ${dirs})
    list(APPEND include_dirs -I${dir})
  endforeach()

  # per target
  get_property(dirs TARGET ${trgt} PROPERTY ${prop_name})
  foreach(dir ${dirs})
    list(APPEND include_dirs -I${dir})
  endforeach()

  get_property(dirs TARGET ${trgt} PROPERTY INTERFACE_${prop_name})
  foreach(dir ${dirs})
    list(APPEND include_dirs -I${dir})
  endforeach()

  get_property(dirs TARGET ${trgt} PROPERTY INTERFACE_SYSTEM_${prop_name})
  foreach(dir ${dirs})
    list(APPEND include_dirs -I${dir})
  endforeach()

  list(REMOVE_DUPLICATES include_dirs)

  debug("@llvmir_extract_include_dirs_properties ${trgt}: ${include_dirs}")

  set(${out_include_dirs} ${include_dirs} PARENT_SCOPE)
endfunction()


function(llvmir_extract_lang_flags out_lang_flags lang)
  set(lang_flags "")

  set(lang_flags ${CMAKE_${lang}_FLAGS_${CMAKE_BUILD_TYPE}})
  set(lang_flags "${lang_flags} ${CMAKE_${lang}_FLAGS}")

  string(REPLACE "\ " ";" lang_flags ${lang_flags})

  debug("@llvmir_extract_lang_flags ${lang}: ${lang_flags}")

  set(${out_lang_flags} ${lang_flags} PARENT_SCOPE)
endfunction()


function(llvmir_extract_standard_flags out_standard_flags trgt)
  set(standard_flags "")

  get_property(std TARGET ${trgt} PROPERTY C_STANDARD)
  get_property(req TARGET ${trgt} PROPERTY C_EXTENSIONS)

  if(std)
    if(req)
      set(cflag "gnu")
    else()
      set(cflag "std")
    endif()

    set(cflag "${flag}c${std}")
  endif()

  get_property(std TARGET ${trgt} PROPERTY CXX_STANDARD)
  get_property(req TARGET ${trgt} PROPERTY CXX_EXTENSIONS)

  if(std)
    if(req)
      set(cxxflag "gnu")
    else()
      set(cxxflag "std")
    endif()

    set(cxxflag "${flag}c++${std}")
  endif()

  if(cflag)
    set(standard_flags "-std=${cflag}")
  endif()

  if(cxxflag)
    set(standard_flags "-std=${cxxflag}")
  endif()

  debug("@llvmir_extract_standard_flags ${lang}: ${standard_flags}")

  set(${out_standard_flags} ${standard_flags} PARENT_SCOPE)
endfunction()


function(llvmir_extract_compile_flags out_compile_flags from)
  #message(DEPRECATION "COMPILE_FLAGS property is deprecated.")

  set(compile_flags "")
  set(prop_name "COMPILE_FLAGS")

  # deprecated according to cmake docs
  if(TARGET ${from})
    get_property(compile_flags TARGET ${from} PROPERTY ${prop_name})
  else()
    get_property(compile_flags SOURCE ${from} PROPERTY ${prop_name})
  endif()

  debug("@llvmir_extract_compile_flags ${from}: ${compile_flags}")

  set(${out_compile_flags} ${compile_flags} PARENT_SCOPE)
endfunction()


