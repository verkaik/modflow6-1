!> @brief This module contains helper routines and parameters for the MODFLOW 6 BMI
!!
!<
module mf6bmiUtil  
  use iso_c_binding, only: c_int, c_char, c_null_char
  use ConstantsModule, only: MAXCHARLEN, LENMEMPATH, LENVARNAME, &
                             LENMODELNAME, LINELENGTH, LENMEMTYPE, &
                             LENMEMADDRESS, LENCOMPONENTNAME
  use KindModule, only: DP, I4B, LGP
  use GenericUtilitiesModule, only: sim_message
  use SimVariablesModule, only: istdout
  use MemoryHelperModule, only: split_mem_address, split_mem_path
  implicit none
  
  ! the following exported parameters will trigger annoying warnings with
  ! the Intel Fortran compiler (4049,4217). We know that these can be ignored:
  !
  ! https://community.intel.com/t5/Intel-Fortran-Compiler/suppress-linker-warnings/td-p/855137
  ! https://community.intel.com/t5/Intel-Fortran-Compiler/Locally-Defined-Symbol-Imported/m-p/900805
  !
  ! and gfortran does so anyway. They have been disabled in the linker config.

  integer(I4B), parameter :: LENGRIDTYPE = 16 !< max length for Fortran grid type string

  integer(c_int), bind(C, name="BMI_LENVARTYPE") :: BMI_LENVARTYPE = LENMEMTYPE + 1 !< max. length for variable type C-strings
  !DEC$ ATTRIBUTES DLLEXPORT :: BMI_LENVARTYPE

  integer(c_int), bind(C, name="BMI_LENGRIDTYPE") :: BMI_LENGRIDTYPE = LENGRIDTYPE + 1 !< max. length for grid type C-strings
  !DEC$ ATTRIBUTES DLLEXPORT :: BMI_LENGRIDTYPE
  
  integer(c_int), bind(C, name="BMI_LENVARADDRESS") :: BMI_LENVARADDRESS = LENMEMADDRESS + 1 !< max. length for the variable's address C-string
  !DEC$ ATTRIBUTES DLLEXPORT :: BMI_LENVARADDRESS

contains
   
  !> @brief Split the variable address string
  !!
  !! Splits the full address string into a memory path and variable name,
  !! following the rules used by the memory manager.
  !<
  subroutine split_address(c_var_address, mem_path, var_name, found)
    use MemoryHelperModule, only: memPathSeparator
    character (kind=c_char), intent(in) :: c_var_address(*) !< full address of a variable
    character(len=LENMEMPATH), intent(out) :: mem_path      !< memory path used by the memory manager
    character(len=LENVARNAME), intent(out) :: var_name      !< name of the variable
    logical(LGP), intent(out)              :: found         !< true when found
    ! local
    character(len=LENMEMPATH) :: var_address 

    ! convert to fortran string
    var_address = char_array_to_string(c_var_address, strlen(c_var_address)) 
    call split_mem_address(var_address, mem_path, var_name)
    call check_mem_address(mem_path, var_name, found)

  end subroutine split_address

  !> @brief Check if the variable exists in the memory manager
  !<
  subroutine check_mem_address(mem_path, var_name, found)
  use MemoryManagerModule, only: get_from_memorylist
  use MemoryTypeModule, only: MemoryType
    character(len=LENMEMPATH), intent(out) :: mem_path      !< memory path used by the memory manager
    character(len=LENVARNAME), intent(out) :: var_name      !< name of the variable
    logical(LGP), intent(out)              :: found         !< true when found
    ! local
    type(MemoryType), pointer :: mt

    found = .false.
    mt => null()

    ! check = false: otherwise stop is called when the variable does not exist
    call get_from_memorylist(var_name, mem_path, mt, found, check=.false.)

  end subroutine check_mem_address

  !> @brief Returns the string length without the trailing null character
  !<
  pure function strlen(char_array) result(string_length)
    character(c_char), intent(in) :: char_array(LENMEMPATH) !< C-style character string
    integer(I4B)                  :: string_length          !< Fortran string length
    integer(I4B) :: i
    
    string_length = 0
    do i = 1, size(char_array)
      if (char_array(i) .eq. C_NULL_CHAR) then
        string_length = i-1
          exit
      end if
    end do
    
  end function strlen

  !> @brief Convert C-style string to Fortran character string
  !<
  pure function char_array_to_string(char_array, length) result(f_string)
    integer(c_int), intent(in) :: length                !< string length without terminating null character
    character(c_char),intent(in) :: char_array(length)  !< string to convert
    character(len=length) :: f_string                   !< Fortran fixed length character string
    integer(I4B) :: i
    
    do i = 1, length
      f_string(i:i) = char_array(i)
    enddo
    
  end function char_array_to_string

  !> @brief Convert Fortran string to C-style character string
  !<
  pure function string_to_char_array(string, length) result(c_array)
  integer(c_int),intent(in) :: length               !< Fortran string length
  character(len=length), intent(in) :: string       !< string to convert
  character(kind=c_char,len=1) :: c_array(length+1) !< C-style character string
  integer(I4B) :: i
  
  do i = 1, length
    c_array(i) = string(i:i)
  enddo
  c_array(length+1) = C_NULL_CHAR
  
  end function string_to_char_array

  !> @brief Extract the model name from a memory address string
  !<
  function extract_model_name(var_address) result(model_name)
    character(len=*), intent(in) :: var_address !< the memory address for the variable
    character(len=LENMODELNAME) :: model_name   !< the extracted model name
    ! local
    character(len=LENMEMPATH) :: mem_path
    character(len=LENCOMPONENTNAME) :: dummy_component
    character(len=LENVARNAME) :: var_name

    call split_mem_address(var_address, mem_path, var_name)
    call split_mem_path(mem_path, model_name, dummy_component)
    
  end function extract_model_name

  !> @brief Get the model name from the grid id
  !<
  function get_model_name(grid_id) result(model_name)
    use ListsModule, only: basemodellist
    use BaseModelModule, only: BaseModelType, GetBaseModelFromList
    integer(kind=c_int), intent(in) :: grid_id  !< grid id
    character(len=LENMODELNAME) :: model_name   !< model name
    ! local
    integer(I4B) :: i
    class(BaseModelType), pointer :: baseModel    
    character(len=LINELENGTH) :: error_msg
    
    model_name = ''
    
    do i = 1,basemodellist%Count()
      baseModel => GetBaseModelFromList(basemodellist, i)
      if (baseModel%id == grid_id) then
        model_name = baseModel%name
        return
      end if
    end do
    
    write(error_msg,'(a,i0)') 'BMI error: no model for grid id ', grid_id
    call sim_message(error_msg, iunit=istdout, skipbefore=1, skipafter=1)
  end function get_model_name

  !> @brief Get the solution object for this index
  !<
  function getSolution(subcomponent_idx) result(solution)
    use SolutionGroupModule
    use NumericalSolutionModule
    use ListsModule, only: basesolutionlist, solutiongrouplist
    integer(I4B), intent(in) :: subcomponent_idx      !< index of solution
    class(NumericalSolutionType), pointer :: solution !< Numerical Solution
    ! local
    class(SolutionGroupType), pointer :: sgp
    integer(I4B) :: solutionIdx
    
    ! this is equivalent to how it's done in sgp_ca
    sgp => GetSolutionGroupFromList(solutiongrouplist, 1)
    solutionIdx = sgp%idsolutions(subcomponent_idx)
    solution => GetNumericalSolutionFromList(basesolutionlist, solutionIdx)    
  end function getSolution

  !> @brief Get the grid type for a named model as a fortran string
  !<
  subroutine get_grid_type_model(model_name, grid_type_f)
    use ListsModule, only: basemodellist
    use NumericalModelModule, only: NumericalModelType, GetNumericalModelFromList
    character(len=LENMODELNAME) :: model_name
    character(len=LENGRIDTYPE) :: grid_type_f
    ! local
    integer(I4B) :: i    
    class(NumericalModelType), pointer :: numericalModel

    do i = 1,basemodellist%Count()
      numericalModel => GetNumericalModelFromList(basemodellist, i)
      if (numericalModel%name == model_name) then
        call numericalModel%dis%get_dis_type(grid_type_f)
      end if
    end do
  end subroutine get_grid_type_model

  !> @brief Confirm that grid is of an expected type
  !< 
  function confirm_grid_type(grid_id, expected_type) result(is_match)
    integer(kind=c_int), intent(in) :: grid_id
    character(len=*), intent(in) :: expected_type
    logical :: is_match
    ! local
    character(len=LENMODELNAME) :: model_name
    character(len=LENGRIDTYPE) :: grid_type
    
    is_match = .false.
     
    model_name = get_model_name(grid_id)
    call get_grid_type_model(model_name, grid_type) 
    ! careful comparison:
    if (expected_type == grid_type) is_match = .true.    
  end function confirm_grid_type

end module mf6bmiUtil