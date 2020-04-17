module SimModule
  
  use KindModule,             only: DP, I4B
  use ConstantsModule,        only: MAXCHARLEN, LINELENGTH,                      &
                                    IUSTART, IULAST,                             &
                                    VSUMMARY, VALL, VDEBUG
  use SimVariablesModule,     only: istdout, iout, isim_level, ireturnerr,       &
                                    iforcestop, iunext
  use GenericUtilitiesModule, only: sim_message, stop_with_error

  implicit none

  private
  public :: count_errors
  public :: store_error
  public :: ustop
  public :: converge_reset
  public :: converge_check
  public :: final_message
  public :: store_warning
  public :: store_note
  public :: count_warnings
  public :: count_notes
  public :: store_error_unit
  public :: store_error_filename
  public :: print_notes
  public :: maxerrors
  
  character(len=MAXCHARLEN), allocatable, dimension(:) :: sim_errors
  character(len=MAXCHARLEN), allocatable, dimension(:) :: sim_warnings
  character(len=MAXCHARLEN), allocatable, dimension(:) :: sim_notes
  integer(I4B) :: nerrors = 0
  integer(I4B) :: maxerrors = 1000
  integer(I4B) :: maxerrors_exceeded = 0
  integer(I4B) :: nwarnings = 0
  integer(I4B) :: nnotes = 0
  integer(I4B) :: inc_errors = 100
  integer(I4B) :: inc_warnings = 100
  integer(I4B) :: inc_notes = 100

contains

function count_errors()
! ******************************************************************************
! Return error count
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- return
  integer(I4B) :: count_errors
! ------------------------------------------------------------------------------
  if (allocated(sim_errors)) then
    count_errors = nerrors
  else
    count_errors = 0
  endif
  return
end function count_errors

function count_warnings()
! ******************************************************************************
! Return warning count
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- return
  integer(I4B) :: count_warnings
! ------------------------------------------------------------------------------
  if (allocated(sim_warnings)) then
    count_warnings = nwarnings
  else
    count_warnings = 0
  endif
  return
end function count_warnings

function count_notes()
! ******************************************************************************
! Return notes count
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- return
  integer(I4B) :: count_notes
! ------------------------------------------------------------------------------
  if (allocated(sim_notes)) then
    count_notes = nnotes
  else
    count_notes = 0
  endif
  return
end function count_notes

subroutine store_error(errmsg)
! ******************************************************************************
! Store an error message for printing at end of simulation
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  use ArrayHandlersModule, only: ExpandArray
  ! -- dummy
  character(len=*), intent(in) :: errmsg
  ! -- local
  logical :: inc_array
  integer(I4B) :: i
! ------------------------------------------------------------------------------
  !
  ! -- determine if the sim_errors should be expanded
  inc_array = .TRUE.
  if (allocated(sim_errors)) then
    if (count_errors() < size(sim_errors)) then
      inc_array = .FALSE.
    end if
  end if
  !
  ! -- resize sim_errors
  if (inc_array) then
    call ExpandArray(sim_errors, increment=inc_errors)
    inc_errors = inc_errors * 1.1
  end if
  !
  ! -- store this error
  i = count_errors() + 1
  if (i <= maxerrors) then
    nerrors = i
    sim_errors(i) = errmsg
  else
    maxerrors_exceeded = maxerrors_exceeded + 1
  end if
  !
  return
end subroutine store_error

subroutine store_error_unit(iunit)
! ******************************************************************************
! Convert iunit to file name and indicate error reading from this file
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- dummy
  integer(I4B), intent(in) :: iunit
  ! -- local
  character(len=LINELENGTH) :: fname
! ------------------------------------------------------------------------------
  !
  inquire(unit=iunit, name=fname)
  call store_error('ERROR OCCURRED WHILE READING FILE: ')
  call store_error(trim(adjustl(fname)))
  !
  return
end subroutine store_error_unit

subroutine store_error_filename(filename)
! ******************************************************************************
! Indicate error reading from this file
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- dummy
  character(len=*), intent(in) :: filename
  ! -- local
! ------------------------------------------------------------------------------
  !
  call store_error('ERROR OCCURRED WHILE READING FILE: ')
  call store_error(trim(adjustl(filename)))
  !
  return
end subroutine store_error_filename

subroutine store_warning(warnmsg)
! ******************************************************************************
! Store a warning message for printing at end of simulation
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  use ArrayHandlersModule, only: ExpandArray
  ! -- dummy
  character(len=*), intent(in) :: warnmsg
  ! -- local
  logical :: inc_array
  integer(I4B) :: i
! ------------------------------------------------------------------------------
  !
  inc_array = .TRUE.
  if (allocated(sim_warnings)) then
    if (count_warnings() < size(sim_warnings)) then
      inc_array = .FALSE.
    end if
  end if
  if (inc_array) then
    call ExpandArray(sim_warnings, increment=inc_warnings)
    inc_warnings = inc_warnings * 1.1
  end if
  i = count_warnings() + 1
  nwarnings = i
  sim_warnings(i) = warnmsg
  !
  return
end subroutine store_warning

subroutine store_note(note)
! ******************************************************************************
! Store a note for printing at end of simulation
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  use ArrayHandlersModule, only: ExpandArray
  ! -- dummy
  character(len=*), intent(in) :: note
  ! -- local
  logical :: inc_array
  integer(I4B) :: i
! ------------------------------------------------------------------------------
  !
  inc_array = .TRUE.
  if (allocated(sim_notes)) then
    if (count_notes() < size(sim_notes)) then
      inc_array = .FALSE.
    end if
  end if
  if (inc_array) then
    call ExpandArray(sim_notes, increment=inc_notes)
    inc_notes = inc_notes * 1.1
  end if
  i = count_notes() + 1
  nnotes = i
  sim_notes(i) = note
  !
  return
end subroutine store_note

logical function print_errors()
! ******************************************************************************
! Print all error messages that have been stored
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- local
  integer(I4B) :: i, isize
  character(len=LINELENGTH) :: errmsg
  ! -- formats
  character(len=*), parameter :: stdfmt = "(/,'ERROR REPORT:',/)"
! ------------------------------------------------------------------------------
  !
  print_errors = .false.
  if (allocated(sim_errors)) then
    isize = count_errors()
    if (isize > 0) then
      print_errors = .true.
      if (iout > 0) write(iout, stdfmt)
      call sim_message('', fmt=stdfmt)
      do i = 1, isize
        call write_message(sim_errors(i))
        if (iout > 0) then
          call write_message(sim_errors(i), iout)
        end if
      enddo
      !
      ! -- write the number of errors
      write(errmsg, '(i0, a)') isize, ' errors detected.'
      call write_message(trim(errmsg))
      if (iout > 0) then
        call write_message(trim(errmsg), iout)
      end if
      !
      ! -- write number of additional errors
      if (maxerrors_exceeded > 0) then
        write(errmsg, '(i0, a)') maxerrors_exceeded,                           &
          ' additional errors detected but not printed.'
        call write_message(trim(errmsg))
        if (iout > 0) then
          call write_message(trim(errmsg), iout)
        end if
      end if
    endif
  endif
  !
  return
end function print_errors

subroutine print_warnings()
! ******************************************************************************
! Print all warning messages that have been stored
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- local
  integer(I4B) :: i, isize
  ! -- formats
  character(len=*), parameter :: stdfmt = "(/,'WARNINGS:',/)"
! ------------------------------------------------------------------------------
  !
  if (allocated(sim_warnings)) then
    isize = count_warnings()
    if (isize>0) then
      if (iout>0) then
        call sim_message('', fmt=stdfmt, iunit=iout)
      end if
      call sim_message('', fmt=stdfmt)
      do i=1,isize
        call write_message(sim_warnings(i))
        if (iout>0) then
          call write_message(sim_warnings(i), iout)
        end if
      end do
    end if
    !
    ! -- write a blank line
    if (iout>0) then
      call sim_message('', iunit=iout)
    end if
    call sim_message('')
  end if
  !
  return
end subroutine print_warnings

subroutine print_notes(numberlist)
! ******************************************************************************
! Print all notes that have been stored
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  ! -- dummy
  logical, intent(in), optional :: numberlist
  ! -- local
  integer(I4B) :: i, isize
  character(len=MAXCHARLEN+10) :: noteplus
  logical :: numlist
  ! -- formats
   character(len=*), parameter :: fmtnotes = "(/,'NOTES:')"
   character(len=*), parameter :: fmta = "(i0,'. ',a)" 
   character(len=*), parameter :: fmtb = '(a)' 
! ------------------------------------------------------------------------------
  !
  if (present(numberlist)) then
    numlist = numberlist
  else
    numlist = .true.
  endif
  !
  if (allocated(sim_notes)) then
    isize = count_notes()
    if (isize>0) then
      if (iout>0) then
        call sim_message('', fmt=fmtnotes, iunit=iout)
      end if
      call sim_message('', fmt=fmtnotes)
      do i=1, isize
        if (numlist) then
          write(noteplus,fmta) i, trim(sim_notes(i))
        else
          write(noteplus,fmtb) trim(sim_notes(i))
        endif
        call write_message(noteplus)
        if (iout > 0) then
          call write_message(noteplus, iout)
        end if
      enddo
    endif
  endif
  !
  return
end subroutine print_notes

subroutine write_message(message, iunit, error, skipbefore, skipafter)
! ******************************************************************************
! Subroutine write_message formats and writes a message.
!
! -- Arguments are as follows:
!       MESSAGE      : message to be written
!       IUNIT        : the unit number to which the message is written
!       ERROR        : if true precede message with "Error"
!       SKIPBEFORE   : number of empty lines before message
!       SKIPAFTER    : number of empty lines after message
!
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- dummy
  character (len=*), intent(in) :: message
  integer(I4B),      intent(in), optional :: iunit
  logical,           intent(in), optional :: error
  integer(I4B),      intent(in), optional :: skipbefore
  integer(I4B),      intent(in), optional :: skipafter
  ! -- local
  integer(I4B)              :: jend, i, nblc, junit, leadblank
  integer(I4B)              :: itake, j
  character(len=20)         :: ablank
  character(len=MAXCHARLEN) :: amessage
! ------------------------------------------------------------------------------
  !
  amessage = message
  if (amessage==' ') return
  if (amessage(1:1).ne.' ') amessage = ' ' // trim(amessage)
  !
  ! -- initialize local variables
  junit = istdout
  ablank = ' '
  itake = 0
  j = 0
  !
  ! -- process optional dummy variables
  if(present(iunit))then
    if (iunit > 0) then
      junit = iunit
    end if
  end if
  if(present(skipbefore))then
    do i = 1, skipbefore
      call sim_message('', iunit=junit)
    end do
  endif
  if(present(error))then
    if(error)then
      nblc=len_trim(amessage)
      amessage=adjustr(amessage(1:nblc+8))
      if(nblc+8.lt.len(amessage)) amessage(nblc+9:)=' '
      amessage(1:8)=' Error: '
    end if
  end if
  !
  do i=1,20
    if (amessage(i:i).ne.' ') exit
  end do
  leadblank=i-1
  nblc=len_trim(amessage)
  !
5 continue
  jend = j + 78 - itake
  if (jend >= nblc) go to 100
  do i=jend,j+1,-1
    if(amessage(i:i).eq.' ') then
      if(itake.eq.0) then
        call sim_message(amessage(j+1:i), iunit=junit)
        itake = 2 + leadblank
      else
        call sim_message(ablank(1:leadblank+2)//amessage(j+1:i), iunit=junit)
      end if
      j = i
      go to 5
    end if
  end do
  if(itake == 0)then
    call sim_message(amessage(j+1:jend), iunit=junit)
    itake = 2 + leadblank
  else
    call sim_message(ablank(1:leadblank+2)//amessage(j+1:jend), iunit=junit)
  end if
  j = jend
  go to 5
  !
100 continue
  jend = nblc
  if (itake == 0)then
    call sim_message(amessage(j+1:jend), iunit=junit)
  else
    call sim_message(ablank(1:leadblank+2)//amessage(j+1:jend), iunit=junit)
  end if
  !
  if(present(skipafter))then
    do i = 1, skipafter
      call sim_message('', iunit=junit)
    end do
  endif
  !
  ! -- return
  return
!  !
!200 continue
!  call ustop()
  !
end subroutine write_message

! -- this subroutine prints final messages and then stops with the active
!    error code.
subroutine ustop(stopmess, ioutlocal, writestd) !PAR
! ******************************************************************************
! Stop program, with option to print message before stopping.
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- dummy
  character, optional, intent(in) :: stopmess*(*)
  integer(I4B),   optional, intent(in) :: ioutlocal
  logical, optional, intent(in) :: writestd !PAR
  !---------------------------------------------------------------------------
  !
  ! -- print the final message
  call print_final_message(stopmess, ioutlocal, writestd) !PAR
  !
  ! -- return appropriate error codes when terminating the program
  call stop_with_error(ireturnerr)
  
end subroutine ustop

subroutine print_final_message(stopmess, ioutlocal, writestd) !PAR
! ******************************************************************************
! Print a final message and close all open files
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
  ! -- modules
  use MpiExchangeGenModule, only: mpi_finalize !PAR
  ! -- dummy
  character, optional, intent(in) :: stopmess*(*)
  integer(I4B),   optional, intent(in) :: ioutlocal  
  logical, optional, intent(in) :: writestd !PAR
  ! -- local
  character(len=*), parameter :: fmt = '(1x,a)'
  character(len=*), parameter :: msg = 'Stopping due to error(s)'
  logical :: errorfound  
  logical :: lwstd !PAR
  !---------------------------------------------------------------------------
  !
  if (present(writestd)) then !PAR
    lwstd = writestd !PAR
  else !PAR
    lwstd = .true. !PAR
  end if !PAR
  !
  call print_notes()
  call print_warnings()
  errorfound = print_errors()
  if (present(stopmess)) then
    if (stopmess.ne.' ') then
      call sim_message(stopmess, fmt=fmt, iunit=iout)
      if (lwstd) call sim_message(stopmess, fmt=fmt) !PAR
      if (present(ioutlocal)) then
        if (ioutlocal > 0 .and. ioutlocal .ne. iout) then
          write(ioutlocal,fmt) trim(stopmess)
          close(ioutlocal)
        endif
      endif
    endif
  endif
  !
  if (errorfound) then
    ireturnerr = 2
    if (iout > 0) then
      call sim_message(stopmess, fmt=fmt, iunit=iout)
    end if
    call sim_message(stopmess, fmt=fmt)
    
    if (present(ioutlocal)) then
      if (ioutlocal > 0 .and. ioutlocal /= iout) write(ioutlocal,fmt) msg
    endif
  endif
  !
  ! -- close all open files
  call sim_closefiles()
  !
  ! -- Finalize MPI if required
  call mpi_finalize() !PAR
  !
  ! -- return
  return

end subroutine print_final_message

subroutine converge_reset()
! ******************************************************************************
! converge_reset
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
    ! -- modules
    use SimVariablesModule, only: isimcnvg
! ------------------------------------------------------------------------------
    !
    isimcnvg = 1
    !
    ! -- Return
    return
  end subroutine converge_reset

  subroutine converge_check(hasConverged)
! ******************************************************************************
! convergence check
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
    ! -- modules
    use SimVariablesModule, only: isimcnvg, numnoconverge, isimcontinue
    ! -- dummy
    logical, intent(inout) :: hasConverged
    ! -- format
    character(len=*), parameter :: fmtfail =                                   &
      "(1x, 'Simulation convergence failure.',                                 &
       &' Simulation will terminate after output and deallocation.')"
! ------------------------------------------------------------------------------
    !
    ! -- Initialize
    hasConverged = .true.
    !
    ! -- Count number of failures
    if(isimcnvg == 0) then
      numnoconverge = numnoconverge + 1
    end if
    !
    ! -- Continue if 'CONTINUE' specified in simulation control file
    if(isimcontinue == 1) then
      if(isimcnvg == 0) then
        isimcnvg = 1
      endif
    endif
    !
    ! --
    if(isimcnvg == 0) then
      !write(iout, fmtfail)
      call sim_message('', fmt=fmtfail, iunit=iout)
      hasConverged = .false.
    endif
    !
    ! -- Return
    return
  end subroutine converge_check

  subroutine final_message()
! ******************************************************************************
! Create the appropriate final message and terminate the program
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
    ! -- modules
    ! -- dummy
    use SimVariablesModule, only: isimcnvg, numnoconverge, ireturnerr
    use MpiExchangeGenModule, only: writestd !PAR
    ! -- local
    character(len=LINELENGTH) :: line
    ! -- formats
    character(len=*), parameter :: fmtnocnvg =                                 &
      "(1x, 'Simulation convergence failure occurred ', i0, ' time(s).')"
! ------------------------------------------------------------------------------
    !
    ! -- Write message if any nonconvergence
    if(numnoconverge > 0) then
      write(line, fmtnocnvg) numnoconverge
      call sim_message(line, iunit=iout)
      call sim_message(line)
    endif
    !
    if(isimcnvg == 0) then
      ireturnerr = 1
      call print_final_message('Premature termination of simulation.', iout, writestd) !PAR
    else
      call print_final_message('Normal termination of simulation.', iout, writestd) !PAR
    endif
    !
    ! -- Return or halt
    if (iforcestop == 1) then
      call stop_with_error(ireturnerr)
    end if
    
  end subroutine final_message
  
  subroutine sim_closefiles()
! ******************************************************************************
! Close all opened files.
! ******************************************************************************
!
!    SPECIFICATIONS:
! ------------------------------------------------------------------------------
    ! -- modules
    implicit none
    ! -- dummy
    ! -- local
    integer(I4B) :: i
    logical :: opened
! ------------------------------------------------------------------------------
    !
    ! -- close all open file units
    do i = iustart, iunext - 1
      !
      ! -- determine if file unit i is open
      inquire(unit=i, opened=opened)
      !
      ! -- skip file units that are no longer open
      if(.not. opened) then
        cycle
      end if
      !
      ! -- close file unit i
      close(i)
    end do
    !
    ! -- return
    return
  end subroutine sim_closefiles
  
end module SimModule
