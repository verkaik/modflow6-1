module MemoryTypeModule
  
  use KindModule, only: DP, I4B
  use ConstantsModule, only: LENORIGIN, LENTIMESERIESNAME, LENVARNAME
  implicit none
  private
  public :: MemoryTSType, MemoryType

  type :: MemoryTSType
    character (len=LENTIMESERIESNAME), pointer :: name => null()
    real(DP), pointer :: value => null()
  end type MemoryTSType
  
  ! -- Integer parameters
  integer(I4B), parameter, public :: ilogicalsclr =  1 !PAR
  integer(I4B), parameter, public :: iintsclr     =  2 !PAR
  integer(I4B), parameter, public :: idblsclr     =  3 !PAR
  integer(I4B), parameter, public :: iaint1d      =  4 !PAR
  integer(I4B), parameter, public :: iaint2d      =  5 !PAR
  integer(I4B), parameter, public :: iaint3d      =  6 !PAR
  integer(I4B), parameter, public :: iadbl1d      =  7 !PAR
  integer(I4B), parameter, public :: iadbl2d      =  8 !PAR
  integer(I4B), parameter, public :: iadbl3d      =  9 !PAR
  integer(I4B), parameter, public :: iats1d       = 10 !PAR
  
  type MemoryType
    character(len=LENVARNAME)                              :: name                   !name of the array
    character(len=LENORIGIN)                               :: origin                 !name of origin
    character(len=50)                                      :: memtype                !type (INTEGER or DOUBLE)
    integer(I4B)                                           :: memitype               !integer type !PAR
    integer(I4B)                                           :: id                     !id, not used
    integer(I4B)                                           :: nrealloc = 0           !number of times reallocated
    integer(I4B)                                           :: isize                  !size of the array
    logical                                                :: master = .true.        !master copy, others point to this one
    logical, pointer                                       :: logicalsclr => null()  !pointer to the logical
    integer(I4B), pointer                                  :: intsclr     => null()  !pointer to the integer
    real(DP), pointer                                      :: dblsclr     => null()  !pointer to the double
    integer(I4B), dimension(:), pointer, contiguous        :: aint1d      => null()  !pointer to 1d integer array
    integer(I4B), dimension(:, :), pointer, contiguous     :: aint2d      => null()  !pointer to 2d integer array
    integer(I4B), dimension(:, :, :), pointer, contiguous  :: aint3d      => null()  !pointer to 3d integer array
    real(DP), dimension(:), pointer, contiguous            :: adbl1d      => null()  !pointer to 1d double array
    real(DP), dimension(:, :), pointer, contiguous         :: adbl2d      => null()  !pointer to 2d double array
    real(DP), dimension(:, :, :), pointer, contiguous      :: adbl3d      => null()  !pointer to 3d double array
    type (MemoryTSType), dimension(:), pointer, contiguous :: ats1d       => null()  !pointer to a time series array
  contains
    procedure :: table_entry
    procedure :: mt_associated
  end type
  
  contains
  
  subroutine table_entry(this, msg)
    class(MemoryType) :: this
    character(len=*), intent(inout) :: msg
    character(len=*), parameter ::                                             &
      fmt = "(1x, a40, a20, a20, i10, i10, a10, a2)"
    character(len=1) :: cptr
    character(len=1) :: dastr
    !
    ! -- Create the msg table entry
    cptr = ''
    if (.not. this%master) cptr = 'T'
    dastr = ''
    if (this%mt_associated() .and. this%isize > 0) dastr='*'
    write(msg, fmt) this%origin, this%name, this%memtype, this%isize,          &
                    this%nrealloc, cptr, dastr
  end subroutine table_entry

  function mt_associated(this) result(al)
    class(MemoryType) :: this
    logical :: al
    al = .false.
    if(associated(this%logicalsclr)) al = .true.
    if(associated(this%intsclr)) al = .true.
    if(associated(this%dblsclr)) al = .true.
    if(associated(this%aint1d)) al = .true.
    if(associated(this%aint2d)) al = .true.
    if(associated(this%aint3d)) al = .true.
    if(associated(this%adbl1d)) al = .true.
    if(associated(this%adbl2d)) al = .true. 
    if(associated(this%adbl3d)) al = .true. 
    if(associated(this%ats1d)) al = .true. 
  end function mt_associated
  
end module MemoryTypeModule